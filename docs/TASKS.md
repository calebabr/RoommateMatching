# RoomMatch Task Tracker

_Last updated: 2026-06-02 by Documentation Agent (Phase 1 P1.1–P1.4 completed)_

---

> **Deployment tags used below:**
> - `[PRE-DEPLOY]` — must be done before Render / Vercel / MongoDB Atlas go live
> - `[POST-DEPLOY]` — can be done after launch; app works without it for beta

---

## In Progress

_Nothing currently in progress._

---

## Completed

| Task | Owner | Closed |
|------|-------|--------|
| Implement JWT authentication end-to-end (register, login, /me) | Auth Agent | prior |
| Hash passwords with bcrypt at explicit `rounds=12` | Auth Agent | prior |
| Strip `hashed_password` from all API responses | Auth Agent | prior |
| Create unique sparse index on `users.email` at startup | Auth Agent / DB Agent | prior |
| Enforce `SECRET_KEY` at startup — raise `RuntimeError` in production if absent | Auth Agent | 2026-05-29 |
| Add `POST /api/auth/change-password` endpoint with current-password validation | Auth Agent | 2026-05-29 |
| Implement password strength validation (`validate_password_strength()` via zxcvbn, min 8 chars, score ≥ 2) | Auth Agent | 2026-05-29 |
| Apply password strength validation at both register and change-password | Auth Agent | 2026-05-29 |
| Implement rate limiting via slowapi — register 3/hr, login 5/15min, change-password 5/hr | Auth Agent | 2026-05-29 |
| Add `get_current_user_or_403` dependency (resource ownership enforcement) | Auth Agent | 2026-05-29 |
| Add `verify_match_exists` dependency (gates chat to matched users only) | Auth Agent | 2026-05-29 |
| Implement auth guard in `AppRoutes` (redirect to /login when `user` is null) | Frontend Agent | 2026-05-29 |
| Implement mobile-responsive sidebar (hamburger menu, backdrop, slide-in drawer) | Frontend Agent | prior |
| Clear both `token` and `roommatch_user` from localStorage on 401 | Frontend Agent | 2026-05-29 |
| Expose `token`, `loading`, `setUser` from `AuthContext` | Frontend Agent | 2026-05-29 |
| Add `unmatchUser` and `getMatchScore` to `api.js` exports | Frontend Agent | 2026-05-29 |
| Make API base URL configurable at runtime via `setApiBase(url)` + localStorage | Frontend Agent | 2026-05-29 |
| Hide Discover and Likes sidebar items when `matchCount >= MAX_MATCHES` | Frontend Agent | 2026-05-29 |
| Consolidate register into single-step full-profile creation | Backend Agent | 2026-05-29 |
| Add `app/limiter.py` with slowapi Limiter (token-keyed, Redis-optional) | Backend Agent | 2026-05-29 |
| Add optional Sentry integration for rate limit violation reporting | Backend Agent | 2026-05-29 |
| Add `pytest.ini` at `backend/pytest.ini` | Tests Agent | 2026-05-29 |
| Add `backend/tests/conftest.py` with isolated `roommatch_test` DB fixture | Tests Agent | 2026-05-29 |
| Write `test_password_security.py` (17 tests — bcrypt, zxcvbn, register/login/change-password) | Tests Agent | 2026-05-29 |
| Write `test_ratelimits.py` (6 async pytest tests for rate limiting) | Tests Agent | 2026-05-29 |
| Write `test_idor.py` (20 async pytest tests for ownership enforcement) | Tests Agent | 2026-05-29 |
| Write `test_idor_integration.py` (15 async pytest tests against live app) | Tests Agent | 2026-05-29 |
| Write `backend/tests/test_auth.py` (24 pytest tests — register, login, /me, round-trip) | Tests Agent | 2026-05-29 |
| Write `backend/tests/test_jwt.py` (14 unit tests — encode/decode, expiry, tamper resistance) | Tests Agent | 2026-05-29 |
| Write `backend/tests/test_password.py` (17 pytest tests — hash rounds, validation, endpoints) | Tests Agent | 2026-05-29 |
| Docs update session — rewriting all 5 agent summaries + creating TASKS.md | Docs Agent | 2026-05-29 |
| Photo upload hardening (B4) — magic bytes validation, 413 for oversized, Pillow re-encode + EXIF strip, dimension check, UUID filenames, Cloudinary storage | Backend Agent + Tests Agent | 2026-05-29 |
| Write `test_photo_upload.py` (12 tests — oversized 413, wrong MIME, fake-extension attack, EXIF stripped, valid jpeg/png/webp, dimension bounds, auth enforcement, UUID filename) | Tests Agent | 2026-05-29 |
| Add `piexif==1.1.3` to `requirements.txt` (test-only dependency for EXIF fixture creation) | Tests Agent | 2026-05-29 |
| MongoDB injection audit (B3) — ~70 queries reviewed across 12 files, 2 findings, 2 notes; report at backend/SECURITY_MONGO_INJECTION.md | Backend Agent | 2026-05-29 |
| Fix FINDING-2 (High): `update_profile` $set exposed sensitive fields — added `_IMMUTABLE_FIELDS` frozenset in `userRoutes.py` stripping `password`, `hashed_password`, `email`, `id`, `matched`, `matchCount`, `matchedWith`, `createdAt` before `$set` | Backend Agent | 2026-05-29 |
| Fix FINDING-1 (Medium): `RegisterRequest` preference fields changed from `Optional[dict]` to `Optional[Preference]` in `authRoutes.py` — operator-injection payloads (e.g. `{"$ne": null}`) now rejected with 422 | Backend Agent | 2026-05-29 |
| Write test_security_findings.py (8 tests — $set field stripping, operator injection rejection, Pydantic coercion behaviour) | Tests Agent | 2026-05-29 |
| Secrets audit (B1) — full repo + git history scan; FINDING-H1 (historical JWT default), FINDING-M1 (IP in dist), FINDING-M2 (MONGO_URL hardcoded); moved MONGO_URL to env var, created root .gitignore, created backend/.env.example + frontendv2/.env.example, removed dist/ from git tracking; report at backend/SECURITY_SECRETS_AUDIT.md | Backend Agent | 2026-05-29 |
| Task B2: Pydantic validation hardening — `Preference.value` 0–10 bounds, `username` 30-char alphanumeric pattern, `bio` 500-char max + HTML strip via `nh3`, `gender` Literal enum, `lifestyleTags` 10-item max + 20-tag whitelist, `ChatMessageCreate.content` 1000-char max + HTML strip, 1 MB body-size middleware (skips upload), clean 422 error format. 41 new tests all passing. | Backend Agent + Tests Agent | 2026-05-29 |
| Add root-level `backend/conftest.py` with `reset_rate_limiter` autouse fixture — prevents slowapi in-memory state from bleeding across test files in the same pytest session | Tests Agent | 2026-05-29 |
| Tighten CORS configuration — replace `allow_origins=["*"]` with env-driven `FRONTEND_URL`, scope methods/headers, add CORS rejection test | Backend Agent + Tests Agent | 2026-06-01 |
| Task C2: Security headers middleware — HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP, Permissions-Policy added via SecurityHeadersMiddleware; 1 test file | Backend Agent + Tests Agent | 2026-06-01 |
| Task H1: Env var sweep — VITE_API_BASE_URL in api.js, JWT_ALGORITHM/JWT_EXPIRATION_HOURS in auth/utils.py, .env.example completeness (Sentry, Redis, JWT sections added). Most items already done in B1/C1/C2. | Backend Agent + Frontend Agent | 2026-06-01 |
| Task H2: Sentry integration — backend FastAPI (sentry-sdk[fastapi]==2.19.2, FastApiIntegration + StarletteIntegration, _before_send filter suppresses 401/403/404/429 and strips Authorization header + cookies, traces_sample_rate=0.1 in prod, send_default_pii=False, /debug/sentry-test endpoint in dev only), frontend @sentry/react (VITE_SENTRY_DSN, VITE_ENV, tracesSampleRate 0.1 in prod, beforeSend strips Authorization), 7 filter unit tests in test_sentry_filter.py. Manual test: set SENTRY_DSN env var, restart backend, hit GET /debug/sentry-test, confirm event in Sentry dashboard. | Backend Agent + Frontend Agent + Tests Agent | 2026-06-01 |
| P1.1 `[PHASE-1]` Fix non-atomic ID generation — replaced `get_next_id()` max-plus-one with `find_one_and_update` + `$inc` on `counters` collection (`upsert=True`, `ReturnDocument.AFTER`); `main.py` lifespan seeds counter from current max ID via `$setOnInsert` on first startup. 2 tests (concurrent + sequential) all passing. | DB Agent + Tests Agent | 2026-06-02 |
| P1.2 `[PHASE-1]` Gate `POST /api/admin/recompute` to admin users only — added `get_admin_user` dependency (reads `ADMIN_USER_IDS` env var as comma-separated integers; raises 403 if caller not in list); upgraded endpoint from `get_current_user`. | Backend Agent | 2026-06-02 |
| P1.3 `[PHASE-1]` Gate `POST /api/uploadUsers` as admin-only — upgraded to `get_admin_user`; endpoint retained for seeding test data. 4 tests (non-admin 403, admin 200 on both endpoints) all passing. | Backend Agent + Tests Agent | 2026-06-02 |
| P1.4 `[PHASE-1]` Password reset / forgot-password flow — backend: `POST /api/auth/forgot-password` (rate-limited 3/hr, SHA-256 token stored on user, always 200) + `POST /api/auth/reset-password` (rate-limited 5/hr, validates hash + expiry, enforces password strength, clears token on success). Frontend: `ForgotPasswordPage`, `ResetPasswordPage`, routes in `App.jsx`, "Forgot password?" link in `LoginPage`, `authForgotPassword`/`authResetPassword` in `api.js`. 7 tests all passing. Note: no email delivery — token returned in API response body (dev/MVP mode). | Backend Agent + Frontend Agent + Tests Agent | 2026-06-02 |

---

## Backlog

---

### 🔨 Phase 1 — Before Render / Vercel / MongoDB Setup `[PHASE-1]`

_Pure code work. Do these locally before touching any deployment infrastructure._

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P1.5 | `[PHASE-1]` Fix `UserDetailPage` like button — uses stale `profile.matched` flag; should reflect current user's actual like/match state | Frontend Agent | High | 2026-06-01 |
| P1.6 | `[PHASE-1]` Write MongoDB index migration script — script that creates all indexes (`users.id`, `likes.fromUser/toUser`, `matches.user1_id/user2_id`, `notifications.toUser`, `recommendations.userId`, `chat_messages.fromUser/toUser`) ready to run against Atlas once it's set up | DB Agent | **Critical** | 2026-06-01 |

---

### 🚀 Phase 2 — After Render / Vercel / MongoDB Setup, Before Beta Launch `[PHASE-2]`

_Infrastructure is up. These are deployment config, data, and verification steps done before inviting any users._

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P2.1 | `[PHASE-2]` Run MongoDB index migration script against Atlas cluster — execute the script from Phase 1 on the production database | DB Agent | **Critical** | 2026-06-01 |
| P2.2 | `[PHASE-2]` Purge or replace the 500 synthetic test users from production DB — they will appear in real users' discovery feeds if left in | DB Agent | **Critical** | 2026-06-01 |
| P2.3 | `[PHASE-2]` Set all Render env vars: `SECRET_KEY`, `MONGO_URL`, `MONGO_DB_NAME`, `CLOUDINARY_*`, `FRONTEND_URL`, `SENTRY_DSN`, `ROOMMATCH_ENV=production` | — | **Critical** | 2026-06-01 |
| P2.4 | `[PHASE-2]` Set all Vercel env vars: `VITE_API_BASE_URL`, `VITE_SENTRY_DSN`, `VITE_ENV=production` | — | **Critical** | 2026-06-01 |
| P2.5 | `[PHASE-2]` Verify `GET /health` returns 200 on the live Render URL | — | **Critical** | 2026-06-01 |
| P2.6 | `[PHASE-2]` Verify `securityheaders.com` scan of production URL returns A grade | — | High | 2026-06-01 |
| P2.7 | `[PHASE-2]` Verify Sentry receives events — hit `GET /debug/sentry-test` on Render, confirm event appears in Sentry dashboard | — | High | 2026-06-01 |
| P2.8 | `[PHASE-2]` Run `POST /api/admin/recompute` once on production DB to seed the recommendations collection | — | **Critical** | 2026-06-01 |
| P2.9 | `[PHASE-2]` Smoke-test full user journey on production: register → discover → like → match → chat | — | **Critical** | 2026-06-01 |
| P2.10 | `[PHASE-2]` Add `POST /api/admin/ban/{user_id}` and `POST /api/admin/unban/{user_id}` endpoints — sets `is_banned: bool` on user document; banned users receive 403 on login; gated by `ADMIN_USER_IDS` env var | Backend Agent | **Critical** | 2026-06-02 |
| P2.11 | `[PHASE-2]` Add protected `/admin` section to frontend — guarded by `is_admin` flag; pages: user list (search/filter), user detail (ban/unban button); keep all admin API calls in a separate `services/adminApi.js` so it can be extracted to a standalone app later | Frontend Agent | **Critical** | 2026-06-02 |
| P2.12 | `[PHASE-2]` Add `ADMIN_USER_IDS` env var to Render and document in `.env.example` — comma-separated list of integer user IDs granted admin access | — | **Critical** | 2026-06-02 |

---

### 🐛 Phase 3 — After Beta Launch (During / After Beta) `[PHASE-3]`

_Beta is live with 100–500 users. Fix bugs surfaced by real usage; add features based on feedback._

#### Auth & Security

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3A.1 | `[PHASE-3]` Implement token refresh mechanism — 24h expiry forces full re-login daily; address once users report it as friction | Auth Agent | Medium | 2026-05-29 |
| P3A.2 | `[PHASE-3]` Add `.edu` email restriction at registration — **will NOT be enforced during beta**; goes in after beta to limit pool to college students | Backend Agent | Medium | 2026-06-01 |
| P3A.3 | `[PHASE-3]` Add email verification on registration — confirm email ownership before activating account | Auth Agent | Medium | 2026-05-29 |
| P3A.4 | `[PHASE-3]` Replace sequential integer user IDs with UUIDs to reduce enumeration risk | Auth Agent | Medium | 2026-05-29 |
| P3A.5 | `[PHASE-3]` Fix NOTE-1: `limit` parameter on `GET /users/{id}/chat/{partner_id}` is unbounded — clamp to max 200 | Backend Agent | Low | 2026-05-29 |

#### Backend Cleanup

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3B.1 | `[PHASE-3]` Mount `chatRoutes.py` or remove it — alternate chat router with timestamp pagination is unreachable | Backend Agent | Medium | 2026-05-29 |
| P3B.2 | `[PHASE-3]` Remove or replace `matchRoutes.py` — legacy in-memory router is dead code | Backend Agent | Low | 2026-05-29 |
| P3B.3 | `[PHASE-3]` Wire `clusterService.py` to a router, or remove it — cluster logic is currently unused | Backend Agent | Low | 2026-05-29 |
| P3B.4 | `[PHASE-3]` Audit and delete `userProfiles.py` — likely stale duplicate of `userProfileService.py` | Backend Agent | Low | 2026-05-29 |
| P3B.5 | `[PHASE-3]` Remove or update `userProfileService.mark_matched` / `unmatch_user` — use old single-int `matchedWith` format, no longer called | Backend Agent | Low | 2026-05-29 |
| P3B.6 | `[PHASE-3]` Expose per-notification mark-read endpoint — `NotificationService.mark_read()` exists but has no route | Backend Agent | Low | 2026-05-29 |
| P3B.7 | `[PHASE-3]` Consolidate `_normalize_matched_with()` — duplicated across `likeService.py`, `chatService.py`, `userProfileService.py` | Backend Agent | Low | 2026-05-29 |

#### Database

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3D.1 | `[PHASE-3]` Enforce `matchedWith` schema — remove the three `_normalize_matched_with()` workarounds with a proper migration | DB Agent | Medium | 2026-05-29 |
| P3D.2 | `[PHASE-3]` Write `compatibilityScore` into `matches` documents — `ConfirmedMatch` model has the field but `likeService` never populates it | DB Agent | Low | 2026-05-29 |
| P3D.3 | `[PHASE-3]` Add TTL index on `notifications` to auto-expire old records | DB Agent | Low | 2026-05-29 |
| P3D.4 | `[PHASE-3]` Add TTL index on `likes` to expire stale pending likes | DB Agent | Low | 2026-05-29 |
| P3D.5 | `[PHASE-3]` Evaluate `clusters` collection — written by `clusterService` but never read for matching; integrate or remove | DB Agent | Low | 2026-05-29 |

#### Tests

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3T.1 | `[PHASE-3]` Write unit tests for `matchScore.py` in isolation (weight calculations, boundary values, simultaneous dealbreakers) | Tests Agent | High | 2026-05-29 |
| P3T.2 | `[PHASE-3]` Add notification creation tests — like-received and match-created events should trigger notifications | Tests Agent | Medium | 2026-05-29 |
| P3T.3 | `[PHASE-3]` Add gender-gate test — users should only see same-gender recommendations | Tests Agent | Medium | 2026-05-29 |
| P3T.4 | `[PHASE-3]` Add MAX_MATCHES cap test — enforce that 5-match limit is respected | Tests Agent | Medium | 2026-05-29 |
| P3T.5 | `[PHASE-3]` Add Vitest + React Testing Library — at minimum test `AuthContext`, `api.js`, and the like/match UI flow | Tests Agent | High | 2026-05-29 |
| P3T.6 | `[PHASE-3]` Add tests for cluster/recommendation algorithm internals | Tests Agent | Low | 2026-05-29 |
| P3T.7 | `[PHASE-3]` Convert `test_api.py` and `test_api_v2.py` from plain Python scripts to proper pytest modules | Tests Agent | Low | 2026-05-29 |

#### Frontend

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3F.1 | `[PHASE-3]` Replace polling-based chat with WebSocket or SSE — address if users report chat feeling slow | Frontend Agent | Medium | 2026-05-29 |
| P3F.2 | `[PHASE-3]` Implement password reset / forgot-password UI flow (backend endpoint from Phase 1 required first) | Frontend Agent | Medium | 2026-06-01 |
| P3F.3 | `[PHASE-3]` Add email verification step to signup flow | Frontend Agent | Medium | 2026-05-29 |
| P3F.4 | `[PHASE-3]` Add pagination to discover, likes, matches, and chat history | Frontend Agent | Medium | 2026-05-29 |
| P3F.5 | `[PHASE-3]` Expand gender options beyond binary male/female in `SignupPage` | Frontend Agent | Medium | 2026-05-29 |
| P3F.6 | `[PHASE-3]` Stop `NotificationBell` polling when user is already on the Notifications page | Frontend Agent | Low | 2026-05-29 |
| P3F.7 | `[PHASE-3]` Expose backend URL setting from within the app (not just login screen) | Frontend Agent | Low | 2026-05-29 |
