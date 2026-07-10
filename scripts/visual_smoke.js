#!/usr/bin/env node
/*
 * Capture repeatable Flutter Web smoke screenshots through Chrome DevTools.
 *
 * Prerequisites:
 * - backend is running
 * - apps/mobile/build/web is served by a static server
 * - Chrome is installed
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const net = require("net");
const crypto = require("crypto");
const { spawn, spawnSync } = require("child_process");

const REPO_ROOT = path.resolve(__dirname, "..");
const DEFAULT_CHROME =
  process.env.CHROME_PATH ||
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

function parseArgs(argv) {
  const args = {
    apiBaseUrl: process.env.LINGBAN_API_BASE_URL || "http://127.0.0.1:8000",
    webBaseUrl: process.env.LINGBAN_WEB_BASE_URL || "http://127.0.0.1:5200",
    artifactDir:
      process.env.SMOKE_ARTIFACT_DIR ||
      path.join(REPO_ROOT, "tmp_visual_checks"),
    chromePath: DEFAULT_CHROME,
    characterId: "yinyue",
    routeMode: process.env.LINGBAN_WEB_ROUTE_MODE || "path",
    width: 390,
    height: 844,
    dpr: 2,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index];
    const value = argv[index + 1];
    if (name === "--api-base-url") {
      args.apiBaseUrl = value;
      index += 1;
    } else if (name === "--web-base-url") {
      args.webBaseUrl = value;
      index += 1;
    } else if (name === "--artifact-dir") {
      args.artifactDir = path.resolve(value);
      index += 1;
    } else if (name === "--chrome-path") {
      args.chromePath = value;
      index += 1;
    } else if (name === "--character-id") {
      args.characterId = value;
      index += 1;
    } else if (name === "--route-mode") {
      args.routeMode = value;
      index += 1;
    }
  }

  return args;
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${options?.method || "GET"} ${url} -> ${response.status}: ${text}`);
  }
  return text ? JSON.parse(text) : {};
}

async function waitForHttp(url, timeoutMs = 30000) {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${url}: ${lastError?.message || "unknown"}`);
}

async function createSmokeUser(args) {
  const email = `codex-ui-${Date.now()}-${Math.random().toString(16).slice(2, 10)}@example.test`;
  const password = "CodexSmokeTest123!";

  const register = await fetchJson(`${args.apiBaseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      nickname: "Codex UI Smoke",
      password,
      birth_date: "1990-01-01",
    }),
  });

  const token = register.access_token;
  assert(token, "register did not return an access token");

  await fetchJson(`${args.apiBaseUrl}/api/v1/characters/select`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ character_id: args.characterId }),
  });

  const seed = spawnSync(
    process.env.PYTHON || "python",
    [
      path.join(REPO_ROOT, "scripts", "visual_smoke_seed.py"),
      "--email",
      email,
      "--character-id",
      args.characterId,
    ],
    {
      cwd: REPO_ROOT,
      env: process.env,
      encoding: "utf8",
      stdio: "pipe",
    },
  );
  if (seed.status !== 0) {
    throw new Error(`visual smoke seed failed: ${seed.stderr || seed.stdout}`);
  }

  return { email, token };
}

function cleanupSmokeUser(email) {
  const cleanup = spawnSync(
    process.env.PYTHON || "python",
    [path.join(REPO_ROOT, "scripts", "cleanup_test_users.py"), "--pattern", email],
    {
      cwd: REPO_ROOT,
      env: process.env,
      encoding: "utf8",
      stdio: "pipe",
    },
  );
  if (cleanup.status !== 0) {
    console.warn(`cleanup failed for ${email}: ${cleanup.stderr || cleanup.stdout}`);
  }
}

function localCanvaskitFile(requestUrl) {
  const canvaskitRoot = path.join(REPO_ROOT, "apps", "mobile", "build", "web", "canvaskit");
  const url = new URL(requestUrl);
  const marker = "/flutter-canvaskit/";
  const markerIndex = url.pathname.indexOf(marker);
  if (markerIndex < 0) return null;

  const relPath = decodeURIComponent(url.pathname.slice(markerIndex + marker.length));
  const parts = relPath.split("/").filter(Boolean);
  const candidates = [
    path.join(canvaskitRoot, ...parts),
    path.join(canvaskitRoot, ...parts.slice(1)),
    path.join(canvaskitRoot, path.basename(relPath)),
    path.join(canvaskitRoot, "chromium", path.basename(relPath)),
    path.join(canvaskitRoot, "experimental_webparagraph", path.basename(relPath)),
  ];

  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function mimeType(filePath) {
  if (filePath.endsWith(".js")) return "application/javascript";
  if (filePath.endsWith(".wasm")) return "application/wasm";
  if (filePath.endsWith(".json")) return "application/json";
  return "application/octet-stream";
}

class SimpleWebSocket {
  constructor(wsUrl, onTextMessage) {
    this.url = new URL(wsUrl);
    this.onTextMessage = onTextMessage;
    this.buffer = Buffer.alloc(0);
    this.fragments = [];
  }

  connect() {
    return new Promise((resolve, reject) => {
      const port = Number(this.url.port || 80);
      const key = crypto.randomBytes(16).toString("base64");
      let handshake = Buffer.alloc(0);
      let connected = false;

      this.socket = net.createConnection(
        { host: this.url.hostname, port },
        () => {
          const requestPath = `${this.url.pathname}${this.url.search}`;
          this.socket.write(
            [
              `GET ${requestPath} HTTP/1.1`,
              `Host: ${this.url.host}`,
              "Upgrade: websocket",
              "Connection: Upgrade",
              `Sec-WebSocket-Key: ${key}`,
              "Sec-WebSocket-Version: 13",
              "",
              "",
            ].join("\r\n"),
          );
        },
      );

      this.socket.on("data", (chunk) => {
        if (!connected) {
          handshake = Buffer.concat([handshake, chunk]);
          const headerEnd = handshake.indexOf("\r\n\r\n");
          if (headerEnd === -1) return;

          const header = handshake.slice(0, headerEnd).toString("utf8");
          if (!header.startsWith("HTTP/1.1 101")) {
            reject(new Error(`WebSocket upgrade failed: ${header.split("\r\n")[0]}`));
            this.socket.destroy();
            return;
          }

          connected = true;
          resolve();
          const rest = handshake.slice(headerEnd + 4);
          if (rest.length > 0) this.parseFrames(rest);
          return;
        }

        this.parseFrames(chunk);
      });

      this.socket.on("error", (error) => {
        if (!connected) reject(error);
        else console.warn(`WebSocket socket error: ${error.message}`);
      });
    });
  }

  send(text) {
    this.socket.write(this.encodeFrame(Buffer.from(text, "utf8"), 0x1));
  }

  close() {
    if (!this.socket || this.socket.destroyed) return;
    try {
      this.socket.write(this.encodeFrame(Buffer.alloc(0), 0x8));
    } catch (_) {
      // Ignore close-frame errors; the process is already shutting down.
    }
    this.socket.end();
  }

  encodeFrame(payload, opcode) {
    const length = payload.length;
    let headerLength = 2;
    if (length >= 126 && length <= 65535) headerLength += 2;
    else if (length > 65535) headerLength += 8;

    const mask = crypto.randomBytes(4);
    const frame = Buffer.alloc(headerLength + 4 + length);
    frame[0] = 0x80 | opcode;

    if (length < 126) {
      frame[1] = 0x80 | length;
    } else if (length <= 65535) {
      frame[1] = 0x80 | 126;
      frame.writeUInt16BE(length, 2);
    } else {
      frame[1] = 0x80 | 127;
      frame.writeBigUInt64BE(BigInt(length), 2);
    }

    mask.copy(frame, headerLength);
    for (let index = 0; index < length; index += 1) {
      frame[headerLength + 4 + index] = payload[index] ^ mask[index % 4];
    }
    return frame;
  }

  parseFrames(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);

    while (this.buffer.length >= 2) {
      const first = this.buffer[0];
      const second = this.buffer[1];
      const fin = Boolean(first & 0x80);
      const opcode = first & 0x0f;
      const masked = Boolean(second & 0x80);
      let length = second & 0x7f;
      let offset = 2;

      if (length === 126) {
        if (this.buffer.length < offset + 2) return;
        length = this.buffer.readUInt16BE(offset);
        offset += 2;
      } else if (length === 127) {
        if (this.buffer.length < offset + 8) return;
        const bigLength = this.buffer.readBigUInt64BE(offset);
        if (bigLength > BigInt(Number.MAX_SAFE_INTEGER)) {
          throw new Error("WebSocket frame too large");
        }
        length = Number(bigLength);
        offset += 8;
      }

      let mask;
      if (masked) {
        if (this.buffer.length < offset + 4) return;
        mask = this.buffer.slice(offset, offset + 4);
        offset += 4;
      }

      if (this.buffer.length < offset + length) return;
      let payload = this.buffer.slice(offset, offset + length);
      this.buffer = this.buffer.slice(offset + length);

      if (masked) {
        payload = Buffer.from(payload);
        for (let index = 0; index < payload.length; index += 1) {
          payload[index] = payload[index] ^ mask[index % 4];
        }
      }

      if (opcode === 0x8) {
        this.socket.end();
        return;
      }
      if (opcode === 0x9) {
        this.socket.write(this.encodeFrame(payload, 0xA));
        continue;
      }
      if (opcode === 0xA) {
        continue;
      }
      if (opcode === 0x1 || opcode === 0x0) {
        if (opcode === 0x1 && this.fragments.length === 0 && fin) {
          this.onTextMessage(payload.toString("utf8"));
          continue;
        }
        this.fragments.push(payload);
        if (fin) {
          this.onTextMessage(Buffer.concat(this.fragments).toString("utf8"));
          this.fragments = [];
        }
      }
    }
  }
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async connect() {
    this.ws = new SimpleWebSocket(this.wsUrl, (data) => this.handleMessage(data));
    await this.ws.connect();
  }

  handleMessage(data) {
    const message = JSON.parse(data);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result || {});
      return;
    }

    if (message.method && this.listeners.has(message.method)) {
      for (const listener of this.listeners.get(message.method)) {
        Promise.resolve(listener(message.params || {})).catch((error) => {
          console.warn(`CDP listener ${message.method} failed: ${error.message}`);
        });
      }
    }
  }

  send(method, params = {}) {
    const id = this.nextId++;
    const payload = JSON.stringify({ id, method, params });
    this.ws.send(payload);
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 30000);
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) || [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  close() {
    this.ws?.close();
  }
}

async function createCdpTab(port) {
  let target;
  const url = `http://127.0.0.1:${port}/json/new?about:blank`;
  try {
    target = await fetchJson(url, { method: "PUT" });
  } catch (_) {
    target = await fetchJson(url);
  }
  const client = new CdpClient(target.webSocketDebuggerUrl);
  await client.connect();
  return client;
}

async function waitForFlutter(client, timeoutMs = 45000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const result = await client.send("Runtime.evaluate", {
      expression:
        "Boolean(document.querySelector('flutter-view') || document.querySelector('flt-glass-pane'))",
      returnByValue: true,
    });
    if (result.result?.value === true) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("Timed out waiting for Flutter DOM nodes");
}

async function navigateToRoute(client, args, route) {
  const base = args.webBaseUrl.replace(/\/$/, "");
  const url = args.routeMode === "hash" ? `${base}/#${route}` : `${base}${route}#${route}`;
  await client.send("Page.navigate", { url });
  await new Promise((resolve) => setTimeout(resolve, 2500));
  await waitForFlutter(client);
}

async function navigateWithinApp(client, route) {
  await client.send("Runtime.evaluate", {
    expression: `window.location.hash = ${JSON.stringify(route)};`,
    returnByValue: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 1800));
  await waitForFlutter(client);
}

async function tap(client, x, y) {
  await client.send("Input.dispatchMouseEvent", {
    type: "mousePressed",
    x,
    y,
    button: "left",
    clickCount: 1,
  });
  await client.send("Input.dispatchMouseEvent", {
    type: "mouseReleased",
    x,
    y,
    button: "left",
    clickCount: 1,
  });
}

async function tapBottomNav(client, args, index) {
  const itemCount = 5;
  const itemWidth = args.width / itemCount;
  const x = itemWidth * index + itemWidth / 2;
  const y = args.height - 34;
  await tap(client, Math.round(x), Math.round(y));
  await new Promise((resolve) => setTimeout(resolve, 1800));
  await waitForFlutter(client);
}

async function pressEscape(client) {
  await client.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    key: "Escape",
    code: "Escape",
    windowsVirtualKeyCode: 27,
  });
  await client.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key: "Escape",
    code: "Escape",
    windowsVirtualKeyCode: 27,
  });
  await new Promise((resolve) => setTimeout(resolve, 600));
}

async function captureCurrentRoute(client, args, route, name, scroll = false) {
  if (scroll) {
    await client.send("Input.dispatchMouseEvent", {
      type: "mouseWheel",
      x: Math.round(args.width / 2),
      y: Math.round(args.height / 2),
      deltaY: 650,
      deltaX: 0,
    });
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  const screenshot = await client.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
  });
  const file = path.join(args.artifactDir, `${name}.png`);
  fs.writeFileSync(file, Buffer.from(screenshot.data, "base64"));
  const bytes = fs.statSync(file).size;
  assert(bytes > 20000, `${name} screenshot looks too small (${bytes} bytes)`);

  const location = await client.send("Runtime.evaluate", {
    expression: "window.location.href",
    returnByValue: true,
  });

  const dom = await client.send("Runtime.evaluate", {
    expression: `(() => {
      const nodes = [...document.querySelectorAll('flutter-view, flt-glass-pane')];
      return {
        title: document.title,
        hasFlutterView: Boolean(document.querySelector('flutter-view')),
        hasGlassPane: Boolean(document.querySelector('flt-glass-pane')),
        nodeCount: nodes.length,
        nodes: nodes.map((node) => {
          const rect = node.getBoundingClientRect();
          return { tag: node.tagName.toLowerCase(), width: rect.width, height: rect.height };
        })
      };
    })()`,
    returnByValue: true,
  });

  return {
    name,
    route,
    file,
    bytes,
    url: location.result?.value,
    viewport: { width: args.width, height: args.height, dpr: args.dpr },
    ...(dom.result?.value || {}),
  };
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  assert(fs.existsSync(args.chromePath), `Chrome not found: ${args.chromePath}`);
  fs.mkdirSync(args.artifactDir, { recursive: true });

  await waitForHttp(`${args.apiBaseUrl.replace(/\/$/, "")}/health`);
  const user = await createSmokeUser(args);

  const port = 9222 + Math.floor(Math.random() * 1000);
  const userDataDir = path.join(os.tmpdir(), `lingban-chrome-smoke-${Date.now()}`);
  const chrome = spawn(args.chromePath, [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ], {
    stdio: "ignore",
  });

  let client;
  try {
    await waitForHttp(`http://127.0.0.1:${port}/json/version`);
    client = await createCdpTab(port);

    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Network.enable");
    await client.send("Fetch.enable", {
      patterns: [{ urlPattern: "*://www.gstatic.com/flutter-canvaskit/*" }],
    });
    client.on("Fetch.requestPaused", async (event) => {
      const filePath = localCanvaskitFile(event.request.url);
      if (!filePath) {
        await client.send("Fetch.continueRequest", { requestId: event.requestId });
        return;
      }
      await client.send("Fetch.fulfillRequest", {
        requestId: event.requestId,
        responseCode: 200,
        responseHeaders: [
          { name: "Content-Type", value: mimeType(filePath) },
          { name: "Access-Control-Allow-Origin", value: "*" },
        ],
        body: fs.readFileSync(filePath).toString("base64"),
      });
    });

    await client.send("Emulation.setDeviceMetricsOverride", {
      width: args.width,
      height: args.height,
      deviceScaleFactor: args.dpr,
      mobile: true,
    });

    const tokenScript = `localStorage.setItem('flutter.access_token', JSON.stringify(${JSON.stringify(user.token)}));`;
    await client.send("Page.addScriptToEvaluateOnNewDocument", { source: tokenScript });
    await client.send("Runtime.evaluate", { expression: tokenScript });

    await navigateToRoute(client, args, "/home");
    await new Promise((resolve) => setTimeout(resolve, 5000));

    const results = [];
    results.push(await captureCurrentRoute(client, args, "/home", "home-smoke"));

    await tapBottomNav(client, args, 1);
    results.push(await captureCurrentRoute(client, args, `/chat/${args.characterId}`, "chat-smoke"));
    await tap(client, 38, args.height - 104);
    await new Promise((resolve) => setTimeout(resolve, 800));
    results.push(
      await captureCurrentRoute(
        client,
        args,
        `/chat/${args.characterId}`,
        "voice-recorder-smoke",
      ),
    );
    await pressEscape(client);

    await tapBottomNav(client, args, 2);
    results.push(await captureCurrentRoute(client, args, `/memory/${args.characterId}`, "memory-smoke"));
    results.push(
      await captureCurrentRoute(
        client,
        args,
        `/memory/${args.characterId}`,
        "memory-scroll-smoke",
        true,
      ),
    );

    await tapBottomNav(client, args, 3);
    results.push(await captureCurrentRoute(client, args, "/emotion", "emotion-smoke"));

    await tapBottomNav(client, args, 4);
    results.push(await captureCurrentRoute(client, args, "/settings", "settings-smoke"));
    results.push(await captureCurrentRoute(client, args, "/settings", "settings-scroll-smoke", true));

    await navigateWithinApp(client, "/subscription");
    results.push(await captureCurrentRoute(client, args, "/subscription", "subscription-smoke"));

    await navigateWithinApp(client, "/about");
    results.push(await captureCurrentRoute(client, args, "/about", "about-smoke"));

    await navigateWithinApp(client, "/privacy");
    results.push(await captureCurrentRoute(client, args, "/privacy", "privacy-smoke"));

    await navigateWithinApp(client, "/terms");
    results.push(await captureCurrentRoute(client, args, "/terms", "terms-smoke"));

    const metadata = {
      email: user.email,
      canvasKit: "local CDP fulfillment for gstatic flutter-canvaskit requests",
      results,
    };
    fs.writeFileSync(
      path.join(args.artifactDir, "visual-smoke.json"),
      JSON.stringify(metadata, null, 2),
    );
    console.log(JSON.stringify(metadata, null, 2));
  } finally {
    client?.close();
    chrome.kill();
    cleanupSmokeUser(user.email);
    fs.rmSync(userDataDir, { recursive: true, force: true });
  }
}

run().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
