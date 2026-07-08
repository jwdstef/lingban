param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$WebBaseUrl = "http://127.0.0.1:5200",
  [switch]$RunApiSmoke,
  [switch]$RunVisualSmoke,
  [switch]$SkipMobileBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$StartedProcesses = @()
$TempServiceDir = Join-Path $RepoRoot "tmp_verify_services"

function Invoke-Step {
  param(
    [string]$Name,
    [string]$WorkingDirectory,
    [scriptblock]$Command
  )

  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  Push-Location $WorkingDirectory
  try {
    $global:LASTEXITCODE = 0
    & $Command
    if ($LASTEXITCODE -ne 0) {
      throw "$Name failed with exit code $LASTEXITCODE"
    }
  }
  finally {
    Pop-Location
  }
}

function Test-HttpOk {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
  }
  catch {
    return $false
  }
}

function Wait-HttpOk {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 45
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-HttpOk $Url) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Timed out waiting for $Url"
}

function Test-LocalUri {
  param([Uri]$Uri)

  return @("127.0.0.1", "localhost", "::1") -contains $Uri.Host
}

function Start-TemporaryBackend {
  $healthUrl = "$($ApiBaseUrl.TrimEnd('/'))/health"
  if (Test-HttpOk $healthUrl) {
    Write-Host "Backend already reachable at $healthUrl" -ForegroundColor DarkGreen
    return
  }

  $uri = [Uri]$ApiBaseUrl
  if (-not (Test-LocalUri $uri)) {
    throw "Backend is not reachable and ApiBaseUrl is not local: $ApiBaseUrl"
  }

  New-Item -ItemType Directory -Force -Path $TempServiceDir | Out-Null
  $stdout = Join-Path $TempServiceDir "backend.out.log"
  $stderr = Join-Path $TempServiceDir "backend.err.log"

  Write-Host "Starting temporary backend at $ApiBaseUrl" -ForegroundColor DarkYellow
  $process = Start-Process `
    -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $uri.Host, "--port", "$($uri.Port)") `
    -WorkingDirectory "$RepoRoot\services\backend" `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru
  $script:StartedProcesses += $process
  Wait-HttpOk $healthUrl 60
}

function Start-TemporaryWebServer {
  if (Test-HttpOk $WebBaseUrl) {
    Write-Host "Web server already reachable at $WebBaseUrl" -ForegroundColor DarkGreen
    return
  }

  $uri = [Uri]$WebBaseUrl
  if (-not (Test-LocalUri $uri)) {
    throw "Web server is not reachable and WebBaseUrl is not local: $WebBaseUrl"
  }

  $webRoot = Join-Path $RepoRoot "apps\mobile\build\web"
  if (-not (Test-Path (Join-Path $webRoot "index.html"))) {
    throw "Mobile web build is missing at $webRoot. Run without -SkipMobileBuild first."
  }

  New-Item -ItemType Directory -Force -Path $TempServiceDir | Out-Null
  $stdout = Join-Path $TempServiceDir "web.out.log"
  $stderr = Join-Path $TempServiceDir "web.err.log"

  Write-Host "Starting temporary static web server at $WebBaseUrl" -ForegroundColor DarkYellow
  $process = Start-Process `
    -FilePath "python" `
    -ArgumentList @("scripts\serve_static_fallback.py", $webRoot, "--host", $uri.Host, "--port", "$($uri.Port)") `
    -WorkingDirectory $RepoRoot `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru
  $script:StartedProcesses += $process
  Wait-HttpOk $WebBaseUrl 30
}

function Stop-TemporaryServices {
  foreach ($process in $StartedProcesses) {
    try {
      if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
      }
    }
    catch {
      Write-Warning "Failed to stop temporary process $($process.Id): $($_.Exception.Message)"
    }
  }
}

try {
  Invoke-Step "Backend compile" "$RepoRoot\services\backend" {
    python -m compileall app tests
  }

  Invoke-Step "Backend migrations" "$RepoRoot\services\backend" {
    alembic upgrade head
  }

  Invoke-Step "Backend unit tests" "$RepoRoot\services\backend" {
    python -m unittest discover -s tests
  }

  Invoke-Step "Mobile pub get" "$RepoRoot\apps\mobile" {
    flutter pub get
  }

  Invoke-Step "Mobile analyze" "$RepoRoot\apps\mobile" {
    dart analyze lib test
  }

  Invoke-Step "Mobile tests" "$RepoRoot\apps\mobile" {
    flutter test
  }

  if (-not $SkipMobileBuild) {
    Invoke-Step "Mobile web build" "$RepoRoot\apps\mobile" {
      flutter build web --dart-define=API_BASE_URL=$ApiBaseUrl --no-wasm-dry-run
    }
  }

  Invoke-Step "Admin install" "$RepoRoot\apps\admin" {
    if (-not (Test-Path node_modules)) {
      npm install
    }
  }

  Invoke-Step "Admin build" "$RepoRoot\apps\admin" {
    npm run build
  }

  if ($RunApiSmoke -or $RunVisualSmoke) {
    Start-TemporaryBackend
  }

  if ($RunApiSmoke) {
    Invoke-Step "API smoke" $RepoRoot {
      python scripts\api_smoke.py --base-url $ApiBaseUrl
    }
  }

  if ($RunVisualSmoke) {
    Start-TemporaryWebServer
    Invoke-Step "Visual smoke" $RepoRoot {
      node scripts\visual_smoke.js --api-base-url $ApiBaseUrl --web-base-url $WebBaseUrl
    }
  }

  Write-Host ""
  Write-Host "All requested verification steps passed." -ForegroundColor Green
}
finally {
  Stop-TemporaryServices
}
