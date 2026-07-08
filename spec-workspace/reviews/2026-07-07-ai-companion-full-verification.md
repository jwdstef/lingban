# AI Companion Full Verification Report

Date: 2026-07-07

## Scope

- Verified against `spec-workspace/prds/ai-companion/PRD.md`.
- Prototype baseline: `spec-workspace/prds/ai-companion/prototype/home-v2-silver.html`, `chat-silver.html`, `memory-silver.html`, `settings-silver.html`, `onboarding.html`.
- Used local `.env` middleware in `services/backend/.env`; Docker was not used.

## Results

| Area | Result | Notes |
| --- | --- | --- |
| Middleware | Pass | PostgreSQL `select 1` passed; Redis `PING=True`; `.env` values were checked without exposing secrets. |
| Migrations | Pass | `alembic upgrade head` resolved to `005_payment_orders`. |
| Backend compile | Pass | `python -m compileall app tests`. |
| Backend unit tests | Pass | `python -m unittest discover -s tests`: 95 tests passed. |
| API smoke | Pass | Auth, profile, characters, selected character, relation, relationship compatibility, settings, memory toggle, admin auth, admin operations, persisted safety review/audit, care frequency/DND, memory search/edit, emotion diary/trend, proactive care click/reply, duplicate reply idempotency, chat SSE, chat voice, automatic emotion diary recording, chat history, data export, and account deletion passed. |
| Mobile analysis | Pass | `dart analyze lib test`: no issues found. |
| Mobile tests | Pass | `flutter test`: 6 tests passed, covering subscription checkout, WeChat payment-channel launch/error states, about, privacy, and terms pages. |
| Mobile Web build | Pass | `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`. |
| Admin build | Pass | `npm run build` passed. |
| Visual smoke | Pass | Chrome CDP screenshots covered home, chat, voice recorder sheet, memory, memory-grid scroll, emotion diary, settings, settings scroll, subscription, about, privacy, and terms at 390x844. |
| Repeatable scripts | Pass | Added reusable API smoke, visual smoke, cleanup, static fallback server, and local `verify_all.ps1`; the verification script now auto-starts temporary local backend/static services when needed, cleans them up, and fails on native command non-zero exit codes. |
| CI gates | Pass | Added GitHub Actions for backend migrations/tests/API smoke, mobile analyze/test/web build, and admin build. |
| Memory management | Pass | Added memory keyword search, memory edit API, mobile search box, edit sheet, and delete controls. |
| User data rights | Pass | Added memory extraction toggle, JSON data export without password hash/raw push tokens, and account deletion request with 30-day scheduled permanent cleanup. |
| Emotion diary | Pass | Added diary/trend APIs, chat-triggered daily recording, mobile trend page, and smoke coverage. |
| Proactive care frequency/DND | Pass | Added care frequency and DND APIs, mobile settings wiring, per-level daily caps/cooldowns, push disable handling, and emotion-trigger enum compatibility. |
| Push Gateway API/provider protocols | Pass with live-credential caveat | Added `/api/v1/push/tokens`, `/api/v1/push/click`, multi-device `push_tokens`, and per-token `push_deliveries`; PushGateway supports JPush REST v3, FCM HTTP v1 service-account OAuth, APNs ES256 provider tokens over HTTP/2, and persists provider message ids when returned. API smoke verifies two-device registration, delivery creation, permission-state persistence, and delivery click回流. Live delivery still requires real provider credentials and device tokens. |
| Admin auth | Pass | Admin APIs require Bearer token, admin login verifies token, and API smoke covers authorized/unauthorized access. |
| Admin P0 operations | Pass | Added admin chat audit, proactive care records, push delivery records, persisted safety events, audit logs, richer user detail metrics, server-side user search, and an operations page in the React admin shell. |
| Safety event audit trail | Pass | High-risk chat content now writes `safety_events`, review actions update status/reviewer/note, and `audit_logs` capture system creation plus admin review. |
| MVP age verification | Pass | Registration now requires `birth_date`, rejects users under 18 before duplicate-account lookup, stores only privacy-minimized age-verification metadata in `users.settings`, and prevents normal settings APIs from overwriting that metadata. |
| Relationship API compatibility | Pass | Added `/api/v1/relationship/{character_id}` and `/api/v1/characters/{character_id}/relationship` aliases while preserving `/api/v1/characters/{character_id}/relation`; API smoke verifies the compatibility contract. |
| Mobile subscription/about/legal | Pass | Added subscription, about, privacy policy, and user agreement routes; settings links now expose subscription management, data export, memory toggle, notification toggle, and 30-day account deletion request. Paid plans now expose upgrade buttons, call the subscription create API, handle unconfigured-provider errors, and pass WeChat payment params into the mobile platform channel. |
| Subscription quota/payment contract | Pass with native/live-pay caveat | Added `/api/v1/subscription`, free/basic/pro plan catalog, daily chat quota calculation, chat/voice quota enforcement, paid cancellation state, mobile subscription status sync, WeChat Pay API v3 APP order creation, local payment order persistence, signed app payment params, callback signature verification, AES-256-GCM notification decrypt, successful-payment subscription activation, mobile payment-channel invocation, and Android/iOS platform scaffolds with native channel stubs. Remaining production work is WeChat OpenSDK integration, Android/iOS build signing, and live merchant callback validation. |
| Voice message MVP | Pass with provider caveat | Backend `/chat/{character_id}/voice` supports multipart audio + transcript fallback + Fish Audio ASR + OpenAI-compatible ASR fallback + optional TTS; mobile mic opens a recorder sheet, records PCM, packages WAV, uploads it, replaces the temp bubble with ASR transcript, and can play TTS audio when returned. Current `.env` still has no Fish Audio key/reference, and the configured OpenAI-compatible gateway exposes no ASR model, so provider-backed live ASR still needs credentials/model availability before production use. |
| Chinese web font | Pass | Bundled `NotoSansSC` font fixes Flutter Web CanvasKit Chinese glyph boxes in visual smoke screenshots. |

## Verified Product Behaviors

- Three official characters are available: `yinyue`, `babata`, `heihaung`.
- `yinyue.color` persists above 32-bit integer range after the BigInteger migration.
- Selecting 银月 initializes the relationship and redirects authenticated users correctly.
- Relationship state is available through the legacy character relation API, the PRD-style standalone relationship API, and the character relationship alias.
- Proactive care reply adds intimacy once; duplicate replies do not double count.
- Push token registration supports multiple active device tokens for one user, PushGateway writes one delivery record per token, stores provider message ids when the upstream returns them, and generic push click回流 marks the delivery plus related proactive message as clicked/delivered.
- User data export includes account profile, settings, relationships, chat, memories, emotion diary, proactive messages, and push metadata while excluding password hash and raw push tokens.
- Memory extraction can be disabled and re-enabled by the user; disabled memory prevents future extraction while preserving existing user-managed memories.
- Account deletion requests require explicit confirmation, disable push, mark the account pending deletion, and schedule permanent deletion after 30 days through the expired-data cleanup task.
- Mobile settings now exposes memory extraction toggle, push notification toggle, data export copy flow, privacy policy, user agreement, subscription management, about page, and account deletion request.
- Subscription page presents the free, advanced, and professional plans, reads backend subscription status, and shows the current plan plus today's remaining chat quota.
- Paid subscription cards now create backend payment orders, pass signed WeChat APP payment params to `lingban/wechat_pay`, and show explicit payment-provider / native-channel status messages.
- Free users are limited by the backend daily chat quota for both text and voice messages; quota exhaustion returns a structured `subscription_limit_reached` error before messages are persisted.
- About and legal pages disclose AI identity, healthy-use principles, data collection scope, user data rights, and crisis-support boundaries.
- Admin operations now support conversation audit, proactive-care record lookup, push-delivery troubleshooting, persisted high-risk safety event review, and audit log lookup behind admin Bearer auth.
- Admin user detail now includes relationship summaries, push-token previews, and per-user counts for chat, memories, proactive messages, and push deliveries.
- Registration enforces the PRD 18+ MVP rule with birth-date verification and avoids storing the full birth date.
- Normal settings updates preserve age-verification metadata so clients cannot overwrite the compliance record after registration.
- Chat SSE returns streamed content and `[DONE]`, then persists user and assistant messages.
- Chat voice endpoint transcribes voice uploads, persists user voice messages, generates assistant replies, records emotion, and triggers memory extraction.
- Voice transcription now tries Fish Audio `/v1/asr` first when `FISH_AUDIO_API_KEY` is configured, then falls back to the OpenAI-compatible ASR path when available.
- Chat voice endpoint can optionally synthesize assistant replies with Fish Audio TTS and return base64 audio metadata without rolling back the chat if TTS is disabled or fails.
- Mobile AI reply bubbles display a play/stop control when TTS audio is returned.
- Home, chat, memory, emotion diary, and settings match the purple-silver prototype direction, including the silver spirit, care card, mood strip, gradient user bubble, memory timeline/category cards, emotion trend chart, and character settings grid.
- Flutter Web screenshots render Chinese text correctly after bundling `NotoSansSC`.

## Fixes Confirmed In This Round

- Active-care reply loop wired from home card to chat reply marking.
- Character color storage changed to BigInteger with migration.
- Auth/onboarding redirect logic fixed.
- Mobile UI aligned to purple-silver prototype theme.
- Memory category icons switched to Material icons to avoid missing glyph boxes.
- Settings character cards tightened so two-line descriptions no longer clip at mobile width.
- Replaced the temporary typed-transcript voice path with a real recorder sheet for the normal mic tap.
- Added repeatable visual coverage for the voice recorder sheet.
- Fixed Flutter Web Chinese tofu boxes by bundling and applying `NotoSansSC`.
- Added optional Fish Audio TTS backend service and `include_tts` support on voice messages.
- Added mobile playback for returned TTS audio via byte-source playback.
- Added Fish Audio ASR support for real voice transcription with OpenAI-compatible fallback.
- Added MVP registration age verification, including backend enforcement, mobile birth-date collection, smoke-script coverage, and privacy-minimized metadata storage.
- Added subscription status and quota contract:
  - `GET /api/v1/subscription` returns current plan, paid-plan status, plan catalog, daily chat quota, and reset time.
  - `POST /api/v1/subscription/create` returns explicit 503 when WeChat Pay is not configured instead of pretending payment succeeded.
  - `POST /api/v1/subscription/cancel` marks paid plans as cancel-at-period-end.
  - Text and voice chat enforce the current plan's daily quota before persistence/ASR/AI calls.
  - Mobile subscription page reads the live subscription endpoint and displays today's remaining chat quota.
- Added WeChat Pay API v3 backend integration:
  - `payment_orders` persists local WeChat payment orders with `out_trade_no`, `prepay_id`, amount, status, transaction id, and provider payload summaries.
  - `POST /api/v1/subscription/create` now creates a local order, calls `/v3/pay/transactions/app`, signs the request with `WECHATPAY2-SHA256-RSA2048`, stores the returned `prepay_id`, and returns signed APP payment params.
  - `POST /api/v1/subscription/wechat/notify` verifies WeChat notification signatures, decrypts AES-256-GCM resources with the API v3 key, marks successful orders paid, and activates/extends the paid subscription.
  - Data export and deletion cleanup now include payment order metadata.
- Added mobile paid-subscription checkout entry:
  - Paid plan cards now show `立即升级` and call `/api/v1/subscription/create`.
  - Successful order creation forwards signed WeChat payment params to the `lingban/wechat_pay` platform channel through `requestPayment`.
  - The subscription page shows clear status for submitted payment requests, missing native payment support, and unconfigured backend payment providers.
- Added Flutter platform scaffolds for native payment work:
  - Generated Android and iOS app projects with bundle/package id `com.lingban.lingban_mobile`.
  - Android `MainActivity` and iOS `AppDelegate` register the `lingban/wechat_pay` channel and return a stable `wechat_pay_sdk_not_configured` error until WeChat OpenSDK is wired.
  - Android manifest includes network, microphone, and notification permissions; iOS display name and microphone usage text now match the product.
- Added Push Gateway provider protocol implementation:
  - JPush sends REST v3 payloads with Basic Auth when app key/master secret are configured and falls back to deterministic local mock behavior otherwise.
  - FCM obtains an OAuth access token with a service-account JWT assertion and sends through HTTP v1 `projects/{project_id}/messages:send` when configured.
  - APNs builds ES256 provider tokens, chooses sandbox/production endpoints from config, sends alert pushes over HTTP/2, and records the returned `apns-id` when present.
  - `push_deliveries.provider_message_id` now stores upstream message ids for later troubleshooting.
- Hardened local full verification:
  - `verify_all.ps1` now treats native command failures from `python`, `flutter`, `npm`, and `node` as script failures.
  - `verify_all.ps1` now auto-starts a temporary FastAPI backend for API/visual smoke when no local backend is listening.
  - `verify_all.ps1` now uses `scripts/serve_static_fallback.py` for Flutter Web visual smoke so client-side routes like `/home` resolve to `index.html`.

## Non-Blocking Warnings

- Flutter dependency resolution reports newer package versions outside current constraints; current pinned versions build and test cleanly.
- Static Web visual smoke needed local CDP fulfillment for Flutter CanvasKit because headless Chrome did not complete the runtime `gstatic/flutter-canvaskit` fetch reliably; this did not change app code or the built JS.
- Live ASR probe without transcript fallback previously failed because the configured OpenAI-compatible gateway returned `model_not_found` for the default ASR model and its model list contains text models only. Fish Audio ASR code support is now present, but current `.env` still does not configure `FISH_AUDIO_API_KEY`; provider-backed live ASR remains externally blocked until that key or another ASR-capable channel is configured.
- Current `.env` middleware is available for local verification, but external production provider credentials are not configured: WeChat Pay app/mch/serial/APIv3 key/private key/platform public key/notify URL, Fish Audio key/reference, JPush key/secret, FCM service-account/project id, and APNs key/team/bundle/private key are all missing. Live provider validation remains blocked by credentials, real device tokens, and native WeChat OpenSDK setup.
- Local Android build is environment-blocked: `flutter build apk --debug` reports `No Android SDK found`. Android SDK, app signing, and WeChat Open Platform app id/signature registration are required before real payment-panel validation.

## Remediation Update

Resolved after the initial verification:

- Flutter analyzer is clean: `dart analyze lib test` reports no issues.
- Added `cupertino_icons` as an explicit mobile dependency; Flutter Web no longer emits the missing `CupertinoIcons` font warning.
- Split the admin build into React, Ant Design, utility, and app chunks; `npm run build` no longer emits the large chunk warning.
- Fixed the `Memory.embedding` ORM mapping to use `pgvector.sqlalchemy.Vector(1536)` instead of `Text`, and added `tests/test_memory_model.py`.
- Verified ORM insertion of a `Memory` row with `embedding=None` against the real PostgreSQL database and cleaned the temporary data.
- Added repeatable verification tooling:
  - `scripts/api_smoke.py`
  - `scripts/visual_smoke.js`
  - `scripts/visual_smoke_seed.py`
  - `scripts/cleanup_test_users.py`
  - `scripts/serve_static_fallback.py`
  - `scripts/verify_all.ps1`
- Added `.github/workflows/ci.yml` with backend, mobile, and admin gates.
- Added user-controlled memory management:
  - `GET /api/v1/memory/{character_id}?query=...` searches content, category, and emotion tags.
  - `PUT /api/v1/memory/{character_id}/{memory_id}` edits content, category, importance, and emotion tags.
  - Editing content clears stale embeddings so old semantic vectors do not keep representing corrected memory text.
  - Mobile memory page now supports search, edit, and delete controls.
- Added user data rights APIs:
  - `PUT /api/v1/memory/toggle` updates `memory_enabled`; `MemoryService.extract_and_store` skips extraction when disabled.
  - `GET /api/v1/data/export` returns portable JSON for the current user's profile, settings, relationships, chat, memories, emotion diary, proactive messages, push tokens, and push deliveries.
  - Export intentionally omits password hashes and raw push token values.
  - `POST /api/v1/data/delete-account` requires `confirm="DELETE"`, disables push, marks the account `pending_deletion`, and schedules deletion 30 days later.
  - `cleanup_expired_data` now permanently deletes due pending-deletion accounts and dependent data.
  - Added `tests/test_data_router.py` and `tests/test_memory_service.py`; expanded `tests/test_memory_router.py`.
- Added relationship API compatibility:
  - `GET /api/v1/relationship/{character_id}` returns the current user's relationship state.
  - `GET /api/v1/characters/{character_id}/relationship` aliases the same behavior for character-scoped clients.
  - Existing `GET /api/v1/characters/{character_id}/relation` remains supported.
  - API smoke includes `relationship_compat`.
  - Added `tests/test_relationship_router.py`.
- Added mobile subscription/about/legal/data-rights surfaces:
  - `GET /api/v1/data/export` is now reachable from mobile settings and copies the portable JSON export to the clipboard.
  - `PUT /api/v1/memory/toggle` is wired to the mobile long-term memory switch.
  - `PUT /api/v1/settings` is wired to the mobile notification switch.
  - `POST /api/v1/data/delete-account` is wired to a guarded mobile delete-account dialog requiring `DELETE`.
  - Added `/subscription`, `/about`, `/privacy`, and `/terms` mobile routes.
  - Added widget tests for subscription, about, privacy, and terms pages.
  - Expanded visual smoke with `settings-scroll-smoke.png`, `subscription-smoke.png`, `about-smoke.png`, `privacy-smoke.png`, and `terms-smoke.png`.
- Added emotion diary:
  - `GET /api/v1/emotion/diary` lists the current user's daily emotion records.
  - `GET /api/v1/emotion/trend` returns trend points, emotion counts, and average intensity.
  - Chat now records detected emotion changes to the current day's diary without changing the SSE response shape.
  - Mobile now has an `情绪日记` page with a 14-day trend chart, emotion chips, daily records, empty state, loading state, and retry state.
- Added proactive-care compatibility for emotion diary:
  - Negative emotion trigger detection now recognizes `anxious`, `sad`, `angry`, `lonely`, and `tired` diary values.
  - Added `tests/test_proactive_service.py`.
- Added Push Gateway API contract coverage:
  - `POST /api/v1/push/tokens` registers or updates the current user's push token, provider, permission status, device ID, and app version metadata.
  - `POST /api/v1/push/click` accepts `delivery_id` or `proactive_message_id` and marks the matching proactive message clicked/delivered.
  - `push_tokens` and `push_deliveries` tables persist multi-device tokens and per-token delivery attempts.
  - PushGateway sends to all active/granted tokens and records delivery status, failure reason, `sent_at`, and `clicked_at`.
  - API smoke includes `push_token_click` with two registered device tokens and two delivery records.
  - Added `tests/test_push_router.py`.
  - Expanded `tests/test_push_service.py`.
- Hardened proactive-care frequency and DND:
  - `PUT /api/v1/care/frequency` updates `proactive_level`.
  - `PUT /api/v1/care/dnd` updates `dnd_enabled`, `dnd_start`, and `dnd_end`.
  - PushGateway now respects `push_enabled`, `proactive_level=off`, per-level daily caps, per-level cooldowns, and DND windows before sending.
  - Mobile settings page now loads settings, updates proactive frequency, and writes the night/DND switch back to the backend.
  - Added `tests/test_push_service.py` and expanded care router tests.
- Added admin authentication:
  - `ADMIN_API_TOKEN` config controls the admin Bearer token.
  - Local debug mode falls back to `dev-admin-token` only when no token is configured.
  - `/api/v1/admin/auth/verify` verifies admin tokens; `/api/v1/admin/*` data routes require admin auth.
  - Admin frontend now has a login page, route guard, token storage, and logout.
  - API smoke verifies missing-token rejection and authorized dashboard access.
- Added admin P0 operations:
  - `GET /api/v1/admin/messages` lists chat messages for conversation audit with user, character, role, type, and search filters.
  - `GET /api/v1/admin/care/messages` lists proactive-care records with user, character, trigger, and push-status filters.
  - `GET /api/v1/admin/push/deliveries` lists per-token push delivery attempts with provider/status filters.
  - `GET /api/v1/admin/safety/events` lists persisted safety events with status, type, severity, user, and character filters.
  - `POST /api/v1/admin/safety/events/{event_id}/review` updates review status, reviewer, note, and review time.
  - `GET /api/v1/admin/audit/logs` lists system/admin audit logs for safety creation and review actions.
  - `GET /api/v1/admin/users/{user_id}` now includes relationship summaries, push-token previews, and operational counts.
  - Admin operations page now has tabs for chat audit, proactive care, push delivery, safety events, and audit logs.
  - Admin frontend now has an `运营排查` route with tabs for chat audit, proactive care, push delivery, and safety events.
  - Fixed the admin axios response interceptor so existing pages read `response.data` correctly at runtime.
  - User management now uses server-side search, admin user detail, and ban/unban actions.
  - API smoke includes `admin_operations` and `safety_review_audit`.
  - Added `tests/test_admin_router.py` and `tests/test_safety_service.py`.
- Added voice message MVP:
  - `POST /api/v1/chat/{character_id}/voice` accepts multipart audio, uses ASR when configured, and keeps transcript fallback for deterministic local smoke.
  - `OPENAI_AUDIO_TRANSCRIPTION_MODEL` controls the ASR model name; the default remains `whisper-1`.
  - `include_tts=true` requests optional TTS audio for the assistant reply.
  - Fish Audio TTS settings are configurable through `FISH_AUDIO_BASE_URL`, `FISH_AUDIO_TTS_MODEL`, `FISH_AUDIO_REFERENCE_ID`, and `FISH_AUDIO_TTS_FORMAT`.
  - Mobile mic tap opens a recorder sheet, records microphone PCM, wraps it as WAV, uploads it, and replaces the temporary voice bubble with the returned transcript.
  - Mobile requests optional TTS for voice messages and renders a play/stop chip on assistant reply bubbles when audio is returned.
  - Long-press mic keeps the transcript fallback sheet for local debugging.
  - Added `tests/test_voice_service.py`, `tests/test_tts_service.py`, and `tests/test_chat_voice_router.py`.
- Added bundled Chinese web font:
  - `NotoSansSC` is registered in Flutter assets and applied via `AppTheme`.
  - Visual smoke screenshots no longer show Chinese glyph boxes.
- Expanded visual smoke:
  - Added `voice-recorder-smoke.png` capture by opening the chat mic recorder sheet.

## Latest Verification Update

Passed after adding scripts and CI:

- `.\scripts\verify_all.ps1`
- `python scripts\api_smoke.py --base-url http://127.0.0.1:8010` against a temporary local backend.
- `node scripts\visual_smoke.js --api-base-url http://127.0.0.1:8000 --web-base-url http://127.0.0.1:5210 --artifact-dir tmp_visual_checks --route-mode path` with a temporary backend and fallback static server.
- `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

Passed after memory search/edit implementation:

- Backend compile: `python -m compileall app tests`.
- Backend tests: `python -m unittest discover -s tests`: 15 tests passed.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- API smoke: includes `memory_search_edit`.
- Visual smoke: memory screenshot confirmed search/edit/delete controls render correctly.
- Local full verification: `.\scripts\verify_all.ps1`.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

Passed after emotion diary implementation:

- Backend compile: `python -m compileall app tests`.
- Backend tests: `python -m unittest discover -s tests`: 31 tests passed.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- API smoke: includes `emotion_diary_trend` and `emotion_diary_record`.
- API smoke: includes `care_frequency_dnd`.
- API smoke: includes `admin_auth`.
- Visual smoke: includes `emotion-smoke.png` with route `/emotion`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Current-state verification after proactive-care compatibility: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke -SkipMobileBuild`.
- Current-state verification after frequency/DND hardening: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Current-state verification after admin auth: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

Passed after voice message, recorder UI, and Chinese font fixes:

- Backend compile: `python -m compileall app tests`.
- Backend voice tests: `python -m unittest tests.test_voice_service tests.test_chat_voice_router`: 5 tests passed.
- Backend tests: `python -m unittest discover -s tests`: 36 tests passed.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Admin build: `npm run build`.
- API smoke: includes `chat_voice`.
- Visual smoke: includes `voice-recorder-smoke.png`; Chinese text renders correctly in `chat-smoke.png`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Live ASR probe without transcript fallback: blocked by provider model availability (`model_not_found`; no audio-like model IDs exposed by the configured gateway).
- Cleanup: retry removed 1 residual UI smoke user after a transient cleanup connection error; final `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users.

Passed after optional TTS implementation and mobile playback wiring:

- Backend compile: `python -m compileall app tests`.
- Backend voice/TTS tests: `python -m unittest tests.test_tts_service tests.test_voice_service tests.test_chat_voice_router`: 10 tests passed.
- Backend tests: `python -m unittest discover -s tests`: 41 tests passed.
- Scripts compile: `python -m compileall scripts`.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

Passed after Fish Audio ASR fallback implementation:

- Backend voice/TTS tests: `python -m unittest tests.test_tts_service tests.test_voice_service tests.test_chat_voice_router`: 13 tests passed.
- Backend compile: `python -m compileall app tests`.
- Scripts compile: `python -m compileall scripts`.
- Backend tests: `python -m unittest discover -s tests`: 44 tests passed.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- API smoke: includes `chat_voice` with deterministic transcript fallback, `tts_status=not_requested`, emotion diary recording, and voice message persistence.
- Visual smoke: includes `voice-recorder-smoke.png` plus home, chat, memory, emotion diary, and settings screenshots.
- Current `.env` provider check without exposing secrets: OpenAI key/base URL are configured; `OPENAI_AUDIO_TRANSCRIPTION_MODEL` is not set and falls back to the default `whisper-1`; Fish Audio key and TTS reference are not configured.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

Passed after Push Gateway API implementation:

- Backend push/care tests: `python -m unittest tests.test_push_router tests.test_push_service tests.test_care_router`: 20 tests passed.
- Backend compile: `python -m compileall app tests`.
- Scripts compile: `python -m compileall scripts`.
- Backend tests: `python -m unittest discover -s tests`: 49 tests passed.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including `push_token_click`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Mobile analysis/tests/web build and admin build passed through `verify_all.ps1`.
- Visual smoke: home, chat, voice recorder, memory, emotion diary, and settings screenshots regenerated successfully.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after multi-device push delivery implementation:

- Added migration `003_push_tokens_deliveries`; `alembic current` reports `003_push_tokens_deliveries (head)`.
- Backend push/care tests: `python -m unittest tests.test_push_router tests.test_push_service tests.test_care_router`: 23 tests passed.
- Backend compile: `python -m compileall app tests`.
- Scripts compile: `python -m compileall scripts`.
- Backend tests: `python -m unittest discover -s tests`: 52 tests passed.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including two-device push token registration, two generated delivery records, and `/api/v1/push/click` with a real delivery id.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Mobile analysis/tests/web build and admin build passed through `verify_all.ps1`.
- Visual smoke: home, chat, voice recorder, memory, emotion diary, and settings screenshots regenerated successfully.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after user data rights implementation:

- Backend data/memory tests: `python -m unittest tests.test_data_router tests.test_memory_router tests.test_memory_service`: 9 tests passed.
- Backend compile: `python -m compileall app tests`.
- Scripts compile: `python -m compileall scripts`.
- Backend tests: `python -m unittest discover -s tests`: 57 tests passed.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including `memory_toggle`, `data_export`, and `data_delete_account`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Mobile analysis/tests/web build and admin build passed through `verify_all.ps1`.
- Visual smoke: home, chat, voice recorder, memory, emotion diary, and settings screenshots regenerated successfully.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after relationship API compatibility implementation:

- Relationship router test: `python -m unittest tests.test_relationship_router`: 1 test passed.
- Backend compile: `python -m compileall app tests`.
- Backend migrations: `alembic current` reports `003_push_tokens_deliveries (head)`.
- Backend tests: `python -m unittest discover -s tests`: 58 tests passed.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including `relationship_compat`, `memory_toggle`, `data_export`, `data_delete_account`, `push_token_click`, and `chat_voice`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke`.
- Mobile analysis/tests/web build and admin build passed through `verify_all.ps1`.
- Visual smoke: home, chat, voice recorder, memory, emotion diary, and settings screenshots regenerated successfully.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped; `tmp_relationship_verify` was removed.

Passed after mobile subscription/about/legal implementation:

- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`: 4 tests passed.
- Mobile web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Visual smoke route fix: in-app hash navigation now captures authenticated child routes instead of being redirected back to home.
- Visual smoke: `node scripts\visual_smoke.js --api-base-url http://127.0.0.1:8000 --web-base-url http://127.0.0.1:5210 --artifact-dir tmp_visual_checks --route-mode path`, including settings scroll, subscription, about, privacy, and terms screenshots.
- Local verification without redundant web rebuild: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -RunVisualSmoke -SkipMobileBuild`.
- Backend tests: `python -m unittest discover -s tests`: 58 tests passed through `verify_all.ps1`.
- API smoke: includes `relationship_compat`, `memory_toggle`, `data_export`, `data_delete_account`, `push_token_click`, and `chat_voice`.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped; `tmp_verify_subscription` was removed.

Passed after admin P0 operations implementation:

- Backend compile: `python -m compileall app tests`.
- Backend admin tests: `python -m unittest tests.test_admin_router tests.test_admin_auth`: 8 tests passed.
- Backend tests: `python -m unittest discover -s tests`: 63 tests passed.
- Scripts compile: `python -m compileall scripts`.
- Admin build: `npm run build`.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including `admin_operations`.
- Local verification without redundant mobile web rebuild: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5210 -RunApiSmoke -SkipMobileBuild`.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend process was stopped; `tmp_verify_admin_ops` was removed.

Passed after persisted safety events and audit logs implementation:

- Added migration `004_safety_events_audit_logs`; `alembic upgrade head` applied it successfully.
- Backend compile: `python -m compileall app tests`.
- Backend targeted tests: `python -m unittest tests.test_admin_router tests.test_admin_auth tests.test_safety_service`: 15 tests passed.
- Backend tests: `python -m unittest discover -s tests`: 70 tests passed.
- Scripts compile: `python -m compileall scripts`.
- Admin build: `npm run build`.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000`, including `admin_operations` and `safety_review_audit`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke`.
- Visual smoke: `node scripts\visual_smoke.js --api-base-url http://127.0.0.1:8000 --web-base-url http://127.0.0.1:5200`, including home, chat, voice recorder, memory, emotion diary, settings, subscription, about, privacy, and terms screenshots.
- Visual screenshot spot check confirmed the key mobile pages render without blank screens, obvious overlap, or broken Chinese glyphs.
- Fixed smoke cleanup ordering so safety events and their audit logs are removed before chat messages.
- Fixed safety review serialization by refreshing the reviewed event after commit to avoid async expired-attribute loading.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after MVP age-verification implementation:

- Backend auth tests: `python -m unittest tests.test_auth_router`: 5 tests passed.
- Backend compile: `python -m compileall app tests`.
- Backend tests: `python -m unittest discover -s tests`: 75 tests passed.
- Scripts compile: `python -m compileall scripts`.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`: 4 tests passed.
- Admin build: `npm run build`.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke`.
- API smoke includes adult `birth_date` on all registration paths and passed all existing checks through `data_delete_account`.
- Visual smoke: `node scripts\visual_smoke.js --api-base-url http://127.0.0.1:8000 --web-base-url http://127.0.0.1:5200`, including home, chat, voice recorder, memory, emotion diary, settings, subscription, about, privacy, and terms screenshots.
- Smoke screenshots spot-checked for home and settings; pages render without blank screens, obvious overlap, or broken Chinese glyphs.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after age-verification metadata protection:

- Added shared settings merge protection so `age_verified`, `age_verified_at`, `age_verification_method`, and `birth_year` cannot be overwritten by normal settings updates.
- Backend targeted tests: `python -m unittest tests.test_auth_router tests.test_settings_router`: 7 tests passed.
- Backend compile: `python -m compileall app tests`.
- Backend tests: `python -m unittest discover -s tests`: 77 tests passed.
- API smoke: `python scripts\api_smoke.py --base-url http://127.0.0.1:8000` passed, including normal settings updates and age-verified registration payloads.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend process was stopped.

Passed after subscription quota contract implementation:

- Backend targeted tests: `python -m unittest tests.test_subscription_service tests.test_subscription_router tests.test_chat_voice_router`: 11 tests passed.
- Backend compile: `python -m compileall app tests`.
- Backend tests: `python -m unittest discover -s tests`: 85 tests passed.
- Scripts compile: `python -m compileall scripts`.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`: 4 tests passed.
- Local full verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke`.
- API smoke includes `subscription` and verifies the free plan catalog/quota response for a newly registered adult user.
- Visual smoke: `node scripts\visual_smoke.js --api-base-url http://127.0.0.1:8000 --web-base-url http://127.0.0.1:5200`, including the dynamic `subscription-smoke.png` page.
- Subscription screenshot spot-check confirmed the page renders current plan and `今日对话剩余 20 / 20 次` without overlap.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after WeChat Pay API v3 backend implementation:

- Backend targeted tests: `python -m unittest tests.test_payment_service tests.test_subscription_router tests.test_subscription_service tests.test_data_router`: 16 tests passed.
- Backend compile/scripts compile: `python -m compileall app tests ..\..\scripts`.
- Backend migrations: `alembic upgrade head` applied `005_payment_orders`.
- Backend tests: `python -m unittest discover -s tests`: 91 tests passed.
- Local static/build verification: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke` completed compile, migrations, backend tests, mobile pub get/analyze/tests/web build, admin build, and API smoke gating; a standalone rerun was used because no backend was listening before the first attempt.
- Standalone API smoke against a temporary local backend passed, including `subscription`, `chat_sse`, `chat_voice`, `data_export`, and payment-order cleanup coverage.
- Visual smoke against temporary local backend/static server passed for home, chat, voice recorder, memory, memory scroll, emotion diary, settings, settings scroll, subscription, about, privacy, and terms.
- Subscription screenshot spot-check confirmed the page still renders current plan and `今日对话剩余 20 / 20 次` without overlap.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed after mobile paid-subscription checkout entry:

- Mobile tests: `flutter test`: 6 tests passed, including paid order creation, WeChat payment-channel launch, and unconfigured-provider error handling.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile Web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Visual smoke against temporary local backend/static server passed for home, chat, voice recorder, memory, memory scroll, emotion diary, settings, settings scroll, subscription, about, privacy, and terms.
- Subscription screenshot spot-check confirmed `立即升级` buttons render on the paid plan cards without text clipping, overlap, or bottom-nav collision.
- Verification script with temporary backend: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke -SkipMobileBuild` passed backend compile/migrations/tests, mobile pub get/analyze/tests, admin build, and API smoke.
- Cleanup: `python scripts\cleanup_test_users.py --dry-run` matched 0 smoke-test users; temporary backend/static processes were stopped.

Passed/checked after Android/iOS platform scaffold:

- Generated Android/iOS Flutter platform directories: `flutter create --platforms=android,ios --org com.lingban --project-name lingban_mobile --no-pub .`.
- Mobile analysis: `dart analyze lib test`: no issues found.
- Mobile tests: `flutter test`: 6 tests passed.
- Mobile Web build: `flutter build web --dart-define=API_BASE_URL=http://127.0.0.1:8000 --no-wasm-dry-run`.
- Android build probe: `flutter build apk --debug` is blocked by local environment with `No Android SDK found`; no APK verification was possible on this machine.

Passed after Push provider protocol implementation and verification-script hardening:

- Provider config check without exposing secrets: OpenAI API key/base URL are configured; `OPENAI_MODEL`, `OPENAI_AUDIO_TRANSCRIPTION_MODEL`, Fish Audio key/reference/model, WeChat Pay credentials/cert paths, JPush key/secret, FCM service-account/project id, and APNs key/team/bundle/private key are missing.
- Backend push/care tests: `python -m unittest tests.test_push_router tests.test_push_service tests.test_care_router`: 27 tests passed.
- Local full verification with automatic temporary backend/static servers: `.\scripts\verify_all.ps1 -ApiBaseUrl http://127.0.0.1:8000 -WebBaseUrl http://127.0.0.1:5200 -RunApiSmoke -RunVisualSmoke`.
- Full verification passed backend compile, `alembic upgrade head`, backend unit tests (`95 tests`), mobile `flutter pub get`, mobile `dart analyze lib test`, mobile `flutter test` (`6 tests`), mobile web build, admin build, API smoke, and visual smoke.
- API smoke passed `health`, adult registration/login/profile, characters, relationship compatibility, settings, subscription quota, memory toggle/search/edit, care frequency/DND, two-device push token/click, care click/reply idempotency, chat SSE, voice message fallback, emotion diary recording, admin operations, safety review/audit, data export, and 30-day account deletion request.
- Visual smoke generated and validated Flutter Web screenshots for home, chat, voice recorder sheet, memory, memory scroll, emotion diary, settings, settings scroll, subscription, about, privacy, and terms at 390x844 with local CanvasKit fulfillment.
- Screenshot spot check confirmed the current pages render Chinese text, bottom navigation, settings, subscription, memory, and emotion diary without blank screens or obvious overlap; the apparent mid-page cutoff on scroll captures is caused by the fixed wheel offset, not bottom-nav occlusion.
- Cleanup dry-run: `python scripts\cleanup_test_users.py --dry-run`: matched 0 smoke-test users.

## Artifacts

- Final screenshots: `tmp_visual_checks/home-final-cdp.png`, `chat-final-cdp.png`, `memory-final-cdp.png`, `memory-grid-final-cdp.png`, `settings-final-cdp.png`.
- Repeatable visual smoke screenshots: `tmp_visual_checks/home-smoke.png`, `chat-smoke.png`, `voice-recorder-smoke.png`, `memory-smoke.png`, `memory-scroll-smoke.png`, `emotion-smoke.png`, `settings-smoke.png`, `settings-scroll-smoke.png`, `subscription-smoke.png`, `about-smoke.png`, `privacy-smoke.png`, `terms-smoke.png`.
- Visual smoke metadata: `tmp_visual_checks/visual-smoke-cdp.json`, `tmp_visual_checks/visual-smoke.json`.

## Cleanup

- Removed temporary logs and token-bearing visual user file.
- Cleaned test users matching `codex-api-%@example.test` and `codex-ui-%@example.test`.
- Stopped temporary backend/static/flutter-run processes.
