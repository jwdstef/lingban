# Lingban Architecture Review

Date: 2026-06-29

## Scope

Reviewed the current repository architecture across:

- `apps/mobile` Flutter app
- `apps/admin` React admin app
- `services/backend` FastAPI backend
- `docker-compose.yml`

## Summary

The repository has a reasonable top-level monorepo split, but the current implementation is closer to an early scaffold than a connected MVP. The main architectural risks are missing API contract alignment, incomplete core product loops, missing database migration/bootstrap flow, and environment assumptions that will prevent mobile/admin/backend from working together reliably.

## Findings

### Critical

1. Admin frontend depends on backend routes that do not exist.

   `apps/admin/src/services/api.ts` calls `/api/v1/admin/users`, `/api/v1/admin/memories`, and `/api/v1/admin/dashboard/*`, but `services/backend/app/main.py` only registers auth, characters, chat, memory, and settings routers. The admin app cannot load real data.

2. Mobile app cannot call protected backend APIs after login/register.

   `apps/mobile/lib/src/shared/services/api_service.dart` leaves token loading/injection as TODO. Backend chat, memory, settings, and character selection require `Authorization: Bearer ...`, so core flows will return 401.

3. Core differentiator is not implemented end to end.

   The PRD positions long-term memory, proactive care, push, and voice calls as MVP core. Current code has placeholder services for memory extraction, push, and Celery proactive tasks. The chat page uses mocked AI replies instead of the backend SSE endpoint.

4. Database schema is not bootstrapped.

   SQLAlchemy models exist, and Alembic is listed in requirements, but no Alembic config/migrations or startup bootstrap are present. Fresh Docker startup will not create tables or seed required character data.

### Important

1. Docker Compose service names do not match default backend URLs.

   `config.py` defaults to `localhost` for Postgres, Redis, and Qdrant. Inside Docker, these need service hostnames such as `postgres`, `redis`, and `qdrant`. This may be handled by `.env`, but the compose file requires `services/backend/.env` and there is no tracked example.

2. Mobile base URL is hard-coded to `http://localhost:8000`.

   On iOS simulator, Android emulator, and physical devices, `localhost` points to the device/simulator, not the developer machine. The app needs environment-based API configuration.

3. Backend transaction handling is risky for streaming responses.

   `get_db()` commits automatically after dependency completion, while `chat.send_message()` also commits inside the SSE generator. Streaming response lifecycle plus session lifetime can become fragile. Split read/write transaction ownership explicitly for streaming endpoints.

4. CORS is permissive while credentials are enabled.

   `allow_origins=["*"]` with `allow_credentials=True` is not production-safe and may behave unexpectedly depending on clients. Use explicit origin config per environment.

5. Generated/garbled text is present in source.

   Many comments, UI labels, and prompt strings display as mojibake. This harms maintainability and may leak garbled copy into product UI and AI prompts.

### Minor

1. Backend returns `({"error": ...}, 404)` in `characters.py` instead of raising `HTTPException`, producing an unexpected JSON shape/status behavior in FastAPI.

2. `Memory.emotion_tags` is annotated as `dict` while configured with `JSONB default=list` and schemas expect `list[str]`.

3. `== True` SQLAlchemy filters should use `.is_(True)` for clarity and lint friendliness.

4. No contract tests or API schema generation workflow exists to keep Flutter, admin, and backend aligned.

## Recommendation

Before expanding features, stabilize the vertical slice:

1. Add environment templates and make Docker/local/mobile API URLs explicit.
2. Add Alembic migrations and character seed data.
3. Implement auth token storage/injection in mobile.
4. Wire mobile chat to backend SSE.
5. Add backend admin routers or remove admin frontend API assumptions.
6. Implement the smallest real proactive-care loop: user setting, scheduled job, push-token registration, push send, delivery log.
7. Generate or document OpenAPI contracts and add basic integration tests.

## Verification

- `python -m compileall services/backend/app` passed.
- `flutter analyze` could not run because `flutter` is not installed in the current shell.
- `npm run build` for admin could not run because dependencies/`tsc` are not installed in `apps/admin`.
