# Lingban Local Development

Lingban is split into a FastAPI backend, a Flutter mobile app, and a React admin app.

## Prerequisites

- Python 3.12
- Flutter/Dart
- Node.js and npm
- PostgreSQL with `pgvector`
- Redis
- Docker Desktop is optional if you want to run PostgreSQL and Redis through `docker compose`

## Backend

If you want Docker-managed middleware, start it from the repo root:

```powershell
docker compose up -d postgres redis
```

If you already have local PostgreSQL and Redis configured, keep using your
`services/backend/.env`; the verification scripts load it directly.

Create the backend environment file when starting from scratch:

```powershell
Copy-Item services/backend/.env.example services/backend/.env
```

Install backend dependencies and run migrations:

```powershell
cd services/backend
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload
```

In another terminal, start Celery worker and beat when testing proactive care:

```powershell
cd services/backend
celery -A app.services.tasks worker --loglevel=info
celery -A app.services.tasks beat --loglevel=info
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

`ANTHROPIC_API_KEY` and `OPENAI_API_KEY` may be left empty for local smoke tests.
When they are empty, the backend uses deterministic local replies, rule-based memory extraction, and rule-based emotion detection so the chat, memory, and emotion diary loops can still be exercised.

## Verification

Run the repeatable local checks from the repo root:

```powershell
.\scripts\verify_all.ps1
```

The default verification runs backend compile, migrations, backend unit tests,
mobile analysis/tests/web build, and admin build.

With the backend already running, add the API smoke path:

```powershell
.\scripts\verify_all.ps1 -RunApiSmoke -ApiBaseUrl http://127.0.0.1:8000
```

With the backend running and `apps/mobile/build/web` served by the fallback
static server, add visual screenshots:

```powershell
python scripts\serve_static_fallback.py apps\mobile\build\web --port 5200
```

Then, from the repo root in another terminal:

```powershell
.\scripts\verify_all.ps1 -RunApiSmoke -RunVisualSmoke -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200
```

Visual artifacts are written to `tmp_visual_checks/`, which is ignored by git.
Temporary users matching `codex-api-%@example.test`, `codex-ui-%@example.test`,
and `codex-memory-%@example.test` can be cleaned manually:

```powershell
python scripts\cleanup_test_users.py
```

## Mobile

The mobile app defaults to `http://localhost:8000` on web and `http://10.0.2.2:8000` on Android emulator in debug mode.
Override the API URL with `API_BASE_URL` when needed:

```powershell
cd apps/mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

For a physical device, use your machine LAN IP:

```powershell
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

## Admin

```powershell
cd apps/admin
npm install
npm run dev
```

The Vite dev proxy points `/api` to `http://localhost:8000`.
Admin APIs require a Bearer token. Set `ADMIN_API_TOKEN` in
`services/backend/.env`; when backend debug mode is enabled and the variable is
empty, local development can use `dev-admin-token`.

## Manual MVP Smoke Path

1. Run Postgres and Redis.
2. Run `alembic upgrade head`.
3. Start the backend.
4. Open the mobile app.
5. Register or log in.
6. Select one character.
7. Send a chat message and confirm streaming response.
8. Open memory after the background extraction task has run.
9. Open emotion diary and confirm the latest emotional chat was recorded.
10. Start Celery beat/worker and confirm proactive care records at `GET /api/v1/care/messages`.
