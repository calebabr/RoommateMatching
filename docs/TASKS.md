# RoomMatch Task Tracker

_Last updated: 2026-06-03 by csp-token-refresh_

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
| P1.5 `[PHASE-1]` Fix `UserDetailPage` like button stale state — `canLike` now uses `alreadyLiked` (from `getLikesSent`) and `alreadyMatched` (from `user.matchedWith`) instead of `profile.matched`; button hides immediately after action; status labels added. 3 tests passing. | Frontend Agent + Tests Agent | 2026-06-02 |
| P1.6 `[PHASE-1]` MongoDB index migration script — `backend/migrate_indexes.py` (synchronous pymongo, idempotent); creates 14 indexes across 6 collections; catches `IndexOptionsConflict`/`IndexKeySpecsConflict` as skips; reads env for `MONGO_URL`/`MONGO_DB_NAME`. 2 tests passing. | DB Agent + Tests Agent | 2026-06-02 |
| P1.2 `[PHASE-1]` Gate `POST /api/admin/recompute` to admin users only — added `get_admin_user` dependency (reads `ADMIN_USER_IDS` env var as comma-separated integers; raises 403 if caller not in list); upgraded endpoint from `get_current_user`. | Backend Agent | 2026-06-02 |
| P1.3 `[PHASE-1]` Gate `POST /api/uploadUsers` as admin-only — upgraded to `get_admin_user`; endpoint retained for seeding test data. 4 tests (non-admin 403, admin 200 on both endpoints) all passing. | Backend Agent + Tests Agent | 2026-06-02 |
| P1.4 `[PHASE-1]` Password reset / forgot-password flow — backend: `POST /api/auth/forgot-password` (rate-limited 3/hr, SHA-256 token stored on user, always 200) + `POST /api/auth/reset-password` (rate-limited 5/hr, validates hash + expiry, enforces password strength, clears token on success). Frontend: `ForgotPasswordPage`, `ResetPasswordPage`, routes in `App.jsx`, "Forgot password?" link in `LoginPage`, `authForgotPassword`/`authResetPassword` in `api.js`. 7 tests all passing. Note: no email delivery — token returned in API response body (dev/MVP mode). | Backend Agent + Frontend Agent + Tests Agent | 2026-06-02 |
| P2.1 `[PHASE-2]` Add `POST /api/admin/ban/{user_id}` and `POST /api/admin/unban/{user_id}` endpoints — sets `is_banned: bool` on user document; `authRoutes.py` login handler raises HTTP 403 if `is_banned` is True (checked after password verification, before token issuance); both endpoints gated by `get_admin_user`. 7 tests all passing (`test_ban.py`). | Backend Agent + Tests Agent | 2026-06-02 |
| P2.2 `[PHASE-2]` Admin frontend app in `frontendAdmin/` (port 3001) — standalone React app with login (admin check), user list (search + status pills), user detail (ban/unban + ConfirmDialog), Sidebar nav, placeholder pages for Errors (P3AD.1) and Feedback (P3AD.2); `adminApi.js` service layer; `is_admin` added to login + `/me` responses in `authRoutes.py`; `GET /api/admin/users` endpoint added to `userRoutes.py`; 5 tests in `test_admin_response.py` all passing. | Backend Agent + Frontend Agent + Tests Agent | 2026-06-02 |
| P3AD.3 `[PHASE-3]` Admin user activity view — backend: `GET /api/admin/users/{user_id}/activity` returns `matches`, `likes_sent`, `chat_partners` aggregated from three collections; missing users shown as "Deleted User"; admin-gated, rate-limited 30/min. Frontend: activity card in `UserDetailPage` (matches table, likes pills, chat partners table); `adminGetUserActivity` in `adminApi.js`; parallel fetch with error isolation. 4 tests in `test_user_activity.py` all passing. | Backend Agent + Frontend Agent + Tests Agent | 2026-06-02 |
| P2.3 `[PHASE-2]` Set all Render env vars: `SECRET_KEY`, `MONGO_URL`, `MONGO_DB_NAME`, `CLOUDINARY_*`, `FRONTEND_URL`, `ADMIN_USER_IDS`, `ROOMMATCH_ENV=production` — all live except `SENTRY_DSN` (pending P2.16) | — | 2026-06-03 |
| P2.4 `[PHASE-2]` Add `ADMIN_USER_IDS` env var to Render | — | 2026-06-03 |
| P2.5 `[PHASE-2]` Set Vercel env vars: `VITE_API_BASE_URL`, `VITE_ENV=production` — all live except `VITE_SENTRY_DSN` (pending P2.16) | — | 2026-06-03 |
| P2.6 `[PHASE-2]` Run MongoDB index migration script against Atlas cluster — 13 indexes created (`users_email_unique` skipped, already existed); all other indexes confirmed `[ok]` | DB Agent | 2026-06-03 |
| P2.7 `[PHASE-2]` Verified Atlas user count = 2 — synthetic test users never reached prod DB; no action needed | DB Agent | 2026-06-03 |
| P2.8 `[PHASE-2]` Verified `GET /health` returns `{"status":"ok"}` on live Render URL | — | 2026-06-03 |
| P2.9 `[PHASE-2]` `securityheaders.com` scan returns A grade — fixed by replacing `BaseHTTPMiddleware` with pure ASGI middleware + CSP updates (`'unsafe-inline'` in `script-src`, production origin in `connect-src`) | Backend Agent | 2026-06-03 |
| P2.11 `[PHASE-2]` Run `POST /api/admin/recompute` on production DB — recomputed recommendations for 2 users | — | 2026-06-03 |
| P2.19 `[PHASE-2]` UptimeRobot monitor live and green — pinging `/health` every 5 min; HEAD method added to endpoint to support free tier | — | 2026-06-03 |
| P2.15 `[PHASE-2]` Deploy `frontendAdmin` to Vercel — live at https://roommatch-admin-hazel.vercel.app; `ADMIN_FRONTEND_URL` added to Render CORS | — | 2026-06-03 |
| P2.16 `[PHASE-2]` Set `SENTRY_DSN` on Render and `VITE_SENTRY_DSN` on Vercel — both projects created, DSNs live | — | 2026-06-03 |
| P2.10 `[PHASE-2]` Verified Sentry receives events — `RuntimeError: Sentry test error — intentional` appeared in roommatch-backend dashboard | — | 2026-06-03 |
| P2.12 `[PHASE-2]` Smoke-test full user journey on production — register → discover → like → match → chat all working | — | 2026-06-03 |
| P2.13 `[PHASE-2]` Verified profile photo persists after save on production | — | 2026-06-03 |
| P2.14 `[PHASE-2]` Verified recompute fires on registration — new account appeared in existing user's discover feed automatically | — | 2026-06-03 |
| P2.20 `[PHASE-2]` Account deletion — soft-delete (`deletedAt` + SHA-256 restore token, 7-day window); restore endpoint (`POST /auth/restore-account`, public); data export (GDPR JSON); hard-delete cascade (all 7 collections + Cloudinary); `cleanup_expired_deletions()` at startup; `DeleteAccountRequest`/`RestoreAccountRequest` models; frontend: Danger Zone in `ProfilePage`, `RestoreAccountPage` at `/restore-account`, `deleteAccount`/`restoreAccount`/`exportUserData` in `api.js`; 15 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P2.21 `[PHASE-2]` Report user system — `ReportReason` enum (6 values); `POST /users/{id}/report/{reported_id}` rate-limited 5/day; auto-block on report; `reports` collection; admin endpoints `GET /admin/reports` + `POST /admin/reports/{id}/resolve`; frontend: Report modal in `UserDetailPage` with dropdown + description textarea; 14 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P2.22 `[PHASE-2]` User block system — `blockService.py` (block/unblock/is_blocked/get_blocked_ids/get_blocked_by_user); auto-unmatch on block; all discover/likes/matches/notifications queries filter blocked IDs bidirectionally; `verify_match_exists` checks block before match; frontend: Block/Unblock button with confirmation overlay in `UserDetailPage`, Blocked Users section in `ProfilePage`; `blockUser`/`unblockUser`/`getBlockedUsers` in `api.js`; 9 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P2.24 `[PHASE-2]` Comprehensive security audit — full OWASP Top 10 (2021) review; report at `backend/SECURITY_AUDIT_FINAL.md`; 2 High findings (VULN-01 unauthenticated matchRoutes, VULN-06 password reset token in response body — both already tracked); 3 Medium, 5 Low; all Critical/High explicitly triaged | Security Audit Agent | 2026-06-03 |
| Password visibility toggle — eye icon show/hide toggle added to all password fields: `LoginPage` (main app + admin), `SignupPage`, `ResetPasswordPage`, `ProfilePage` delete account modal | Frontend Agent | 2026-06-03 |
| P3A.1 `[PHASE-3]` Token refresh mechanism — `POST /api/auth/refresh` (30-day rotation) + `POST /api/auth/logout` (server-side invalidation); frontend queued 401 interceptor auto-refreshes silently; `refresh_token` in login/register responses; 8 tests all passing | Auth Agent | 2026-06-03 |
| P3A.6 `[PHASE-3]` Remove `'unsafe-inline'` from CSP — full frontend CSS migration (21 new CSS files, 18 source files migrated from inline styles to className); `'unsafe-inline'` removed from both `script-src` and `style-src` in SecurityHeadersMiddleware; CSP assertions updated in `test_security_headers.py` | Frontend Agent + Backend Agent + Tests Agent | 2026-06-03 |
| P3B.11 `[PHASE-3]` Backend layout cleanup — 19 `test_*.py` moved from `backend/` root → `backend/tests/`; root `conftest.py` deleted (fixture already in `tests/conftest.py`); 5 `SECURITY_*.md` reports moved to `docs/security/`; `usersTest500.json` moved to `backend/app/test/`; `testpaths = tests` added to `pytest.ini` | Orchestrator | 2026-06-03 |
| P3A.1 `[PHASE-3]` Token refresh mechanism — backend: `_generate_refresh_token` helper, `POST /api/auth/refresh` (10/hr, rotates token), `POST /api/auth/logout` (10/hr, `$unset` clears refresh hash), `TokenResponse.refresh_token`, `RefreshRequest` model; login + register now issue 30d refresh tokens. Frontend: `saveRefreshToken`/`loadRefreshToken`/`clearRefreshToken` in `api.js`, `authRefresh`/`authLogout` API functions, queued 401 interceptor with `_isRefreshing` flag + `_refreshQueue`; `AuthContext` login/signup save refresh_token, logout is async + calls server-side logout. 8 tests all passing. | Auth Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P3A.6 `[PHASE-3]` Full CSP unsafe-inline removal — 21 new CSS files in `frontendv2/src/styles/` (`theme.css`, `utilities.css`, 13 per-page, 5 per-component); `main.jsx` imports all; 18 source files migrated from `style={{...}}` to `className`; remaining inline styles are legitimately dynamic (toggle state, slider gradient, sidebar position, score-based colors); `backend/app/main.py` CSP updated: `'unsafe-inline'` removed from `style-src` and `script-src`; `test_security_headers.py` updated with `not in` assertions confirming absence. | Frontend Agent + Backend Agent + Tests Agent | 2026-06-03 |

---

## Backlog

---

### 🔨 Phase 1 — Before Render / Vercel / MongoDB Setup `[PHASE-1]`

_All Phase 1 tasks complete. See Completed table above._

---

### 🚀 Phase 2 — After Render / Vercel / MongoDB Setup, Before Beta Launch `[PHASE-2]`

_Infrastructure is up. These are deployment config, data, and verification steps done before inviting any users._

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P2.23 | `[PHASE-2]` Email domain validator at signup — restrict to `.edu` emails (configurable via `ALLOWED_EMAIL_DOMAINS` env var); block disposable email providers using `disposable-email-domains` package; normalize emails (lowercase, strip whitespace); server-side only; return friendly error "Please sign up with your @auburn.edu address." | Backend Agent | **Critical** | 2026-06-03 |
| P2.25 | `[PHASE-2]` PostHog product analytics — install `posthog-js` in frontend; capture key events: signup_started, signup_completed, email_verified, profile_completed, photo_uploaded, like_sent (formerly "swipe_right" — app uses a Like button, not gestures), profile_skipped (formerly "swipe_left" — requires Skip button from P3FT.4 before this event fires), match_created, message_sent, login, logout, account_deleted; identify users by user ID after login; pull `POSTHOG_API_KEY` / `VITE_POSTHOG_KEY` from env vars | Frontend Agent | Medium | 2026-06-03 |

---

### 🐛 Phase 3 — After Beta Launch (During / After Beta) `[PHASE-3]`

_Beta is live with 100–500 users. Fix bugs surfaced by real usage; add features based on feedback._

#### Auth & Security

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3A.2 | `[PHASE-3]` Add `.edu` email restriction at registration — **will NOT be enforced during beta**; goes in after beta to limit pool to college students | Backend Agent | Medium | 2026-06-01 |
| P3A.3 | `[PHASE-3]` ~~Add email verification on registration~~ — **merged into P3FT.2**; P3FT.2 now covers the full flow (token infra + SendGrid delivery + login block). Do not implement P3A.3 separately. | — | — | merged 2026-06-03 |
| P3A.4 | `[PHASE-3]` Replace sequential integer user IDs with UUIDs to reduce enumeration risk | Auth Agent | Medium | 2026-05-29 |
| P3A.5 | `[PHASE-3]` Fix NOTE-1: `limit` parameter on `GET /users/{id}/chat/{partner_id}` is unbounded — clamp to max 200 | Backend Agent | Low | 2026-05-29 |
| P3A.7 | `[PHASE-3]` Privacy Policy and Terms of Service — generate via Termly or iubenda; customize for photo storage, message storage, .edu email collection, third-party data sharing (Cloudinary, SendGrid, Sentry, PostHog, Atlas, Render, Vercel); add explicit consent checkbox (not pre-checked) to signup flow; include data retention policy, right to export, and account deletion rights | — | **Critical** | 2026-06-03 |

#### Features

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3FT.1 | `[PHASE-3]` Age verification (18+) at signup — add `dateOfBirth` field; reject users under 18 at registration endpoint; display-layer note in ToS; add to `SignupPage`. **Existing user migration:** users without a `dateOfBirth` on file see a one-time modal on next app open requiring them to enter their date of birth before proceeding; if under 18, their account is automatically banned (with a message explaining why) until they reach 18; if 18+, they confirm and continue normally. Backend: store `dateOfBirth`, add age-check on register, add `POST /api/users/{id}/submit-age` endpoint for existing users, auto-ban logic. Frontend: age gate modal in `App.jsx` that fires when `user.dateOfBirth` is missing. | Backend Agent + Frontend Agent | High | 2026-06-03 |
| P3FT.2 | `[PHASE-3]` Email verification on signup (absorbs P3A.3) — generate 32-byte cryptographically random token (24h expiry) on register; store `email_verification_token_hash` + `email_verification_expires` + `is_email_verified: false` on user; send token via SendGrid; block login (403 "email not verified") until verified; `POST /api/auth/verify-email` endpoint; resend endpoint (rate-limited 3/hr per email); unverified banner in frontend; `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` env vars | Backend Agent + Frontend Agent | High | 2026-06-03 |
| P3FT.3 | `[PHASE-3]` Profile pause and deactivation — "Pause" toggle: hidden from discover, still in existing matches/chats, reversible; "Deactivate": hidden from everyone including matches, reversible within 30 days then auto-soft-deletes; both require password re-entry and send confirmation email | Backend Agent + Frontend Agent | Medium | 2026-06-03 |
| P3FT.4 | `[PHASE-3]` Rejection cooldown — **Note: the app has no swipe gestures; "swipe left/right" is Tinder shorthand.** This task requires two parts: (1) add a Skip/Pass button to DiscoverPage (Frontend Agent) so users can explicitly reject a profile — currently no such action exists; (2) track skips in a new `swipes` collection or extend `likes`; suppress skipped profiles from that user's discover feed for 30 days via TTL index + discover query filter (Backend Agent + DB Agent) | Backend Agent + Frontend Agent + DB Agent | Medium | 2026-06-03 |
| P3FT.5 | `[PHASE-3]` Auto-moderation on uploads and bios — photos: Cloudinary moderation add-on (or AWS Rekognition fallback) flags explicit/violent content → set `pending_review`, hide from discover until admin approves; bios: OpenAI moderation endpoint on create/update → `pending_review` if flagged; usernames: `better-profanity` filter at signup; admin queue endpoint for pending content | Backend Agent + Frontend Agent | Medium | 2026-06-03 |
| P3FT.6 | `[PHASE-3]` Match email notifications — on mutual match, send both users a SendGrid email with: match preview (name, photo, 1-2 lifestyle tags), deep link to chat, unsubscribe link; `emailOnMatch` user preference toggle (default true); respect SendGrid 100/day free-tier cap with graceful fallback | Backend Agent | Medium | 2026-06-03 |
| P3FT.7 | `[PHASE-3]` Admin audit log — immutable append-only `admin_audit_log` collection; fields: timestamp, adminUserId, action, targetUserId, targetResourceId, reason, ipAddress; every admin endpoint writes an entry before returning; `GET /admin/audit-log` (admin-only, paginated); no update/delete endpoints | Backend Agent + Frontend Agent | Medium | 2026-06-03 |

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
| P3B.11 | `[PHASE-3]` Consolidate backend test and docs layout — moved all 19 loose `test_*.py` files from `backend/` root into `backend/tests/`; deleted redundant root `conftest.py` (rate-limiter fixture already present in `backend/tests/conftest.py`); moved all 5 `SECURITY_*.md` audit reports to `docs/security/`; moved `usersTest500.json` to `backend/app/test/`; added `testpaths = tests` to `pytest.ini` | Orchestrator | Low | 2026-06-03 |
| P3B.10 | `[PHASE-3]` Replace startup-only `cleanup_expired_deletions` with a scheduled job — currently runs once at app startup; long-running processes will not hard-delete expired soft-deleted accounts until next restart; replace with APScheduler (daily job) or an OS-level cron on the Render host | Backend Agent | Low | 2026-06-03 |
| P3B.8 | `[PHASE-3]` Move recommendation recompute to FastAPI BackgroundTasks — `on_new_user` currently runs synchronously, blocking registration and profile-save responses as O(N) DB writes; switching to `background_tasks.add_task(...)` returns the response instantly and runs recompute after; new user's discover feed may lag a few seconds but registration is unblocked. | Backend Agent | Medium | 2026-06-03 |
| P3B.9 | `[PHASE-3]` Trigger recompute on profile save when preferences change significantly — only recompute if any preference score shifts by ≥ 2 points (on 0–10 scale) OR any deal-breaker status toggles; rate-limit to 1 recompute per user per hour to prevent rapid-save abuse; implement alongside P3B.8 (BackgroundTasks) so profile save response is never blocked | Backend Agent | Medium | 2026-06-03 |

#### Database

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3D.1 | `[PHASE-3]` Enforce `matchedWith` schema — remove the three `_normalize_matched_with()` workarounds with a proper migration | DB Agent | Medium | 2026-05-29 |
| P3D.2 | `[PHASE-3]` Write `compatibilityScore` into `matches` documents — `ConfirmedMatch` model has the field but `likeService` never populates it | DB Agent | Low | 2026-05-29 |
| P3D.3 | `[PHASE-3]` Add TTL index on `notifications` to auto-expire old records | DB Agent | Low | 2026-05-29 |
| P3D.4 | `[PHASE-3]` Add TTL index on `likes` to expire stale pending likes | DB Agent | Low | 2026-05-29 |
| P3D.5 | `[PHASE-3]` Evaluate `clusters` collection — written by `clusterService` but never read for matching; integrate or remove | DB Agent | Low | 2026-05-29 |
| P3D.9 | `[PHASE-3]` Restrict MongoDB Atlas network access to Render's egress IPs only — remove `0.0.0.0/0`; requires upgrading Render to Starter ($7/mo) for static outbound IPs; defer until after beta when paid tier is warranted | — | High | 2026-06-03 |
| P3D.8 | `[PHASE-3]` MongoDB Atlas backup restore test — upgrade Atlas cluster to M2+ (paid tier required for backups), enable backups, restore a snapshot to a new cluster and confirm data integrity; defer until after beta when data is worth protecting | — | High | 2026-06-03 |
| P3D.6 | `[PHASE-3]` Add TTL index on `recommendations` collection — expire after 7 days (stale recommendations should be recomputed, not served indefinitely) | DB Agent | Medium | 2026-06-03 |
| P3D.7 | `[PHASE-3]` DB performance review — run `explain()` on every hot query, document the index that supports each; audit matching algorithm complexity at 5000 users; add Redis or Mongo TTL caching for top-matches (serve cached up to 1 hour, recompute on-demand); written report at `backend/PERFORMANCE_INDEXES.md` | DB Agent + Backend Agent | High | 2026-06-03 |

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

#### Admin Dashboard

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3AD.1 | `[PHASE-3]` Add error/bug log view to admin dashboard — surface Sentry events via Sentry API (requires `SENTRY_AUTH_TOKEN` + `SENTRY_ORG`/`SENTRY_PROJECT` env vars); backend proxy endpoint `GET /api/admin/errors` returns recent Sentry issues; admin dashboard renders them in a table. Depends on Sentry live on production (P2.10). | Backend Agent + Frontend Agent | Medium | 2026-06-02 |
| P3AD.2 | `[PHASE-3]` Add user feedback system — backend: `POST /api/feedback` (authenticated, stores `{user_id, message, created_at}` in `feedback` collection) + `GET /api/admin/feedback` (admin-gated, returns all submissions); main app: feedback button/modal accessible from sidebar; admin dashboard: feedback inbox page showing all submissions with user info and timestamp. | Backend Agent + Frontend Agent | Medium | 2026-06-02 |
| P3AD.4 | `[PHASE-3]` Implement reported conversation moderation — users can flag a chat conversation for review (`POST /api/chat/{partner_id}/report`); admin dashboard shows a "Reports" inbox with flagged conversations (full message history visible only for reported chats); admin can dismiss or act (ban) from the same view. Depends on P3AD.2 (feedback/reporting infrastructure). | Backend Agent + Frontend Agent | Medium | 2026-06-02 |
| P3AD.5 | `[PHASE-3]` Content moderation queue in admin dashboard — list all `pending_review` photos and bios; admin can approve or reject; approve clears flag and makes visible; reject removes content and notifies user; depends on P3FT.5 (auto-moderation) | Frontend Agent | Medium | 2026-06-03 |
| P3AD.6 | `[PHASE-3]` Audit log viewer in admin dashboard — paginated table of `admin_audit_log` entries (timestamp, admin, action, target); read-only; depends on P3FT.7 | Frontend Agent | Medium | 2026-06-03 |

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

---

### 🚀 Phase 4 — Campus-Wide Launch `[PHASE-4]`

_App is fully built. This phase is about confirming readiness and executing the launch._

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P4.1 | `[PHASE-4]` Load test before launch — Locust or k6 test: 500 concurrent users, mix of signup (5%), login (10%), discover + like/skip (60%), chat (20%), profile view (5%); targets: p95 < 500ms, error rate < 0.5%; run against staging; document bottlenecks and file fixes as new tasks | Backend Agent | High | 2026-06-03 |
