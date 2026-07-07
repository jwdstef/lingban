# Lingban Local Development

Lingban is split into a FastAPI backend, a Flutter mobile app, and a React admin app.

## Prerequisites

- Docker Desktop
- Python 3.12
- Flutter/Dart
- Node.js and npm

## Backend

Start local infrastructure from the repo root:

```powershell
docker compose up -d postgres redis
```

Create the backend environment file:

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
When they are empty, the backend uses deterministic local replies and rule-based memory extraction so the chat and memory loop can still be exercised.

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

## MVP Smoke Path

1. Run Postgres and Redis.
2. Run `alembic upgrade head`.
3. Start the backend.
4. Open the mobile app.
5. Register or log in.
6. Select one character.
7. Send a chat message and confirm streaming response.
8. Open memory after the background extraction task has run.
9. Start Celery beat/worker and confirm proactive care records at `GET /api/v1/care/messages`.
