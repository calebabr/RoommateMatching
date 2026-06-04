# RoomMatch Task Tracker

_Last updated: 2026-06-04 by docs-agent (ux-polish-mobile-fixes)_

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
| P2.25 `[PHASE-2]` PostHog product analytics — `posthog-js` installed; guarded `posthog.init()` in `main.jsx` (no-op without `VITE_POSTHOG_API_KEY`); `identify` + `login`/`signup_completed`/`logout` in `AuthContext`; `signup_started` (once per session via ref, on Email field focus) in `SignupPage`; `photo_uploaded`, `profile_completed`, `account_deleted` in `ProfilePage`; `match_created` / `like_sent` in `UserDetailPage`; `message_sent` in `ChatPage`; env var is `VITE_POSTHOG_API_KEY` (spec originally said `VITE_POSTHOG_KEY`); `profile_skipped` and `email_verified` deferred (require P3FT.4 and P3FT.2 respectively) | Frontend Agent | 2026-06-03 |
| P2.28 `[PHASE-2]` Clickable chat header — `ChatPage.jsx` `.chat-partner-info` div made clickable; clicking partner avatar or username navigates to `/user/:id`; pointer cursor + opacity hover effect via `headerHovered` state | Frontend Agent | 2026-06-03 |
| P2.27 `[PHASE-2]` Age verification (18+) — `calculate_age()` helper in `auth/utils.py`; `dateOfBirth` field on `RegisterRequest` (400 if under 18); `POST /api/users/{id}/submit-age` (5/hr, auth+ownership, auto-ban under 18); `SubmitAgeRequest` model; `AgeGateModal` in `App.jsx` (fires when `user.dateOfBirth` falsy, calls `submitAge`); `dateOfBirth` date input in `SignupPage` step 0 with client-side age check; `submitAge` in `api.js`; 12 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P2.26 `[PHASE-2]` Privacy Policy, Terms of Service, consent checkbox, and ToS versioning — `PrivacyPolicyPage` at `/privacy` (8 sections), `TermsOfServicePage` at `/terms` (10 sections), `LegalPage.css` shared styles; `agreedToTerms` checkbox in `SignupPage` (unchecked by default, links to `/terms` + `/privacy`, sends `termsVersion: "2026-06-03"` in payload); `AcceptTermsRequest` model; `termsVersion` + `termsAcceptedAt` stored at registration; `POST /api/users/{id}/accept-terms` endpoint (10/hr); `CURRENT_TERMS_VERSION` + `TERMS_CHANGELOG` constants in `App.jsx`; `ToSModal` (blocking, changelog banner, checkbox guard, calls `acceptTerms`); early-return AppRoutes order: age gate → ToS modal → routes; `/privacy` and `/terms` public routes; `acceptTerms` in `api.js` | Backend Agent + Frontend Agent | 2026-06-03 |
| P3AD.1 `[PHASE-3]` Sentry error viewer in admin dashboard — `GET /api/admin/errors` backend proxy to Sentry REST API (last 25 issues, 7d window); admin-gated, 30/min rate limit; graceful `{"error":"Sentry not configured","issues":[]}` if env vars absent; `ErrorsPage.jsx` replaced placeholder with table (Title/Level/Status/First Seen/Last Seen/Times Seen), colour-coded level pills, Sentry permalink links, warning banner when unconfigured. **Requires `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` on Render to show live data.** | Backend Agent + Frontend Agent | 2026-06-03 |
| P3AD.2 `[PHASE-3]` User feedback system — `feedback_collection` in `database.py`; `FeedbackCreate` model; `POST /api/feedback` (auth, 10/hr) + `GET /api/admin/feedback` (admin, 60/min, username joined); `submitFeedback(message)` in `api.js`; `FeedbackModal` + "Send Feedback" sidebar button in `App.jsx` (textarea, 2000-char limit + counter, success/error states); `adminGetFeedback` in `adminApi.js`; `FeedbackPage.jsx` replaced placeholder with table (User/Message/Submitted); 6 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| P3AD.4 `[PHASE-3]` Reported conversation moderation — `conversation_reports_collection` in `database.py`; `ConversationReportCreate` + `ResolveConversationReport` models; `POST /api/chat/{partner_id}/report` (auth, 5/hr, verifies match) + 3 admin endpoints (list, messages, resolve with dismiss/ban actions); `adminGetConversationReports`, `adminGetReportMessages`, `adminResolveConversationReport` in `adminApi.js`; `ReportsPage.jsx` (new page: pending reports table, expandable message thread, Dismiss/Ban with confirm dialog); `/reports` route in `App.jsx`; Reports nav item in `Sidebar.jsx`; removed stale "(P3AD.1)"/"(P3AD.2)" labels from sidebar; 10 tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-03 |
| Chat read receipts (iMessage-style) — new `chat_read_status` MongoDB collection; `POST /api/chat/{partner_id}/mark-read` (upsert, 60/min) + `GET /api/users/{user_id}/unread-chats` (returns `{unread_count, unread_partner_ids}`, 60/min); `GET /chat/{partner_id}` now returns `{messages, partner_last_read_at}`; `timezone` import bug fix in `userRoutes.py`; frontend: unread badge on Chat nav icon (polls 10s in `App.jsx`), blue dot + bold username for unread convos in `ChatListPage`, mark-read on open/poll + "New messages" divider + "Seen [time]" receipt + relative timestamps in `ChatPage`; `markChatRead` + `getUnreadChats` added to `api.js`; 9 tests in `test_chat_read_receipts.py` all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-04 |
| Religion tag — optional `religionTag` field on `RegisterRequest`/`UserCreate`; single-select pill section in `SignupPage` Step 2; edit + display in `ProfilePage`; display in `UserDetailPage`; display-only, no scoring impact | Backend Agent + Frontend Agent | 2026-06-04 |
| Major field — optional `major` field on `RegisterRequest`/`UserCreate`; dropdown + "Other" free-text in `SignupPage` Step 0; edit + display in `ProfilePage`; display in `UserDetailPage`; display-only, no scoring impact | Backend Agent + Frontend Agent | 2026-06-04 |
| Graduation year & season — optional `graduationSeason` (string) + `graduationYear` (int) fields on `RegisterRequest`/`UserCreate`; dual season/year dropdowns in `SignupPage` Step 0; edit + display in `ProfilePage`; display in `UserDetailPage`; display-only, no scoring impact | Backend Agent + Frontend Agent | 2026-06-04 |
| P2.29 `[PHASE-2]` Cancel pending like — `DELETE /api/users/{user_id}/like/{liked_user_id}` removes like doc from `likes` collection (blocks if match exists, 404 if not found); frontend: "Sent Likes" section in `LikesPage` with Cancel button per entry; `cancelLike(userId, likedUserId)` added to `api.js`; tests all passing | Backend Agent + Frontend Agent + Tests Agent | 2026-06-04 |
| P3T.1 `[PHASE-3]` matchScore.py unit tests — weight calculations, boundary values, simultaneous dealbreakers; test file at `backend/tests/test_match_score.py` | Tests Agent | 2026-06-04 |
| P3FT.3 `[PHASE-3]` Profile pause and deactivation — `POST /users/{id}/pause` + `POST /users/{id}/unpause` (no password); `POST /users/{id}/deactivate` (requires password, sets `is_deactivated` + `deactivatedAt`) + `POST /users/{id}/reactivate`; paused users hidden from discover/likes-received; deactivated users hidden everywhere including existing matches; frontend: pause toggle and deactivate flow with password confirmation in `ProfilePage`; 2026-06-04 |  Backend Agent + Frontend Agent + Tests Agent | 2026-06-04 |
| P3FT.4 `[PHASE-3]` Skip/pass button + swipes collection — `POST /api/users/{user_id}/skip/{skipped_user_id}` (upsert with TTL, 60/min); `swipes_collection` in `database.py`; `GET /top-matches` filters skipped IDs; frontend: Skip button on `DiscoverPage` beside Like; `skipUser(userId, skippedUserId)` in `api.js`; 30-day TTL index on `skipped_at`; tests all passing | Backend Agent + Frontend Agent + DB Agent + Tests Agent | 2026-06-04 |
| Unread badge immediate clear on chat open — `useEffect` on `location.pathname` in `App.jsx` filters partner from `unreadChatPartnerIds` state immediately on `/chat/:id` navigation; no longer waits for 10-second poll | Frontend Agent | 2026-06-04 |
| "Seen" receipt real-time tick update — `tick` state in `ChatPage.jsx` increments every 30s; forces `formatSeenTime` re-renders so relative timestamps update without a full poll; `setPartnerLastReadAt` called on every poll response | Frontend Agent | 2026-06-04 |
| Terms/Privacy converted to in-app LegalModal — new `LegalModal.jsx` component (scrollable, dark-themed, 85vh, full text inline); all `<a href="/terms">` and `<a href="/privacy">` navigation links replaced with LegalModal-opening buttons in `App.jsx`, `NotificationBell.jsx`, `SignupPage.jsx` | Frontend Agent | 2026-06-04 |
| Feedback modal aesthetic improvements — FeedbackModal in `NotificationBell.jsx` restyled: accent-colored title, dark textarea with focus ring, ghost cancel button, filled accent submit button, centered success state | Frontend Agent | 2026-06-04 |
| Religion tag purple color — religion tag pills now use soft purple palette (`rgba(139,92,246,0.2)` bg, `#a78bfa` text, `rgba(139,92,246,0.3)` border) in `ProfilePage.jsx` and `UserDetailPage.jsx` | Frontend Agent | 2026-06-04 |
| Major "Major: " label prefix — `major` field prefixed with `"Major: "` in display mode in `ProfilePage.jsx` and `UserDetailPage.jsx` | Frontend Agent | 2026-06-04 |
| ProfileCompletionModal soft prompt — new inline component in `App.jsx`; fires when user is missing `major` or graduation fields; Save calls `updateUser`; "Skip for now" dismisses for session | Frontend Agent | 2026-06-04 |
| PrivacyPolicyPage + TermsOfServicePage text updated for major/graduation data — Privacy adds major/graduation to collected data list; ToS Section 2 notes fields are optional | Frontend Agent | 2026-06-04 |
| Full mobile responsiveness audit — `@media (max-width: 768px)` blocks in 11 CSS files; grid overflows fixed on Discover/Likes/Matches; ChatPage keyboard/scroll fixed (flex+min-height, safe-area insets, 16px inputs, iOS zoom prevention); 44px touch targets everywhere; Modal converted to bottom-sheet; two-column layouts stack to single column | Frontend Agent | 2026-06-04 |

---

## Backlog

---

### 🔨 Phase 1 — Before Render / Vercel / MongoDB Setup `[PHASE-1]`

_All Phase 1 tasks complete. See Completed table above._

---

### 🚀 Phase 2 — After Render / Vercel / MongoDB Setup, Before Beta Launch `[PHASE-2]`

_Infrastructure is up. These are deployment config, data, and verification steps done before inviting any users._

_All Phase 2 tasks complete. See Completed table above._

---

### 🐛 Phase 3 — After Beta Launch (During / After Beta) `[PHASE-3]`

_Beta is live with 100–500 users. Fix bugs surfaced by real usage; add features based on feedback._

#### Auth & Security

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3A.2 | `[PHASE-3]` Add `.edu` email restriction at registration — **will NOT be enforced during beta**; goes in after beta to limit pool to college students; restrict to `.edu` emails (configurable via `ALLOWED_EMAIL_DOMAINS` env var); block disposable email providers using `disposable-email-domains` package; normalize emails (lowercase, strip whitespace); return friendly error "Please sign up with your @auburn.edu address." | Backend Agent | Medium | 2026-06-01 |
| P3A.4 | `[PHASE-3]` Replace sequential integer user IDs with UUIDs to reduce enumeration risk | Auth Agent | Medium | 2026-05-29 |
| P3A.5 | `[PHASE-3]` Fix NOTE-1: `limit` parameter on `GET /users/{id}/chat/{partner_id}` is unbounded — clamp to max 200 | Backend Agent | Low | 2026-05-29 |

#### Features

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3FT.2 | `[PHASE-3]` Email verification on signup (absorbs P3A.3) — generate 32-byte cryptographically random token (24h expiry) on register; store `email_verification_token_hash` + `email_verification_expires` + `is_email_verified: false` on user; send token via SendGrid; block login (403 "email not verified") until verified; `POST /api/auth/verify-email` endpoint; resend endpoint (rate-limited 3/hr per email); unverified banner in frontend; `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` env vars | Backend Agent + Frontend Agent | High | 2026-06-03 |
| P3FT.8 | `[PHASE-3]` Email & admin notifications for account state changes — when a user pauses, deactivates, or deletes their account, send them a confirmation email and notify admins of deactivations/deletions; depends on SendGrid setup (P3FT.2); add after email infrastructure is in place | Backend Agent | Medium | 2026-06-04 |
| P3FT.9 | `[PHASE-3]` Real-time typing indicator in chat — show "User is typing..." animation in ChatPage when the other user is actively typing; options: (a) fast-polling approach with a POST /chat/{partner_id}/typing endpoint that sets a TTL flag in Redis/DB, polled every 1–2s; (b) WebSocket upgrade (see P3F.1); implement (a) first as a lightweight solution | Backend Agent + Frontend Agent | Medium | 2026-06-04 |
| P3FT.5 | `[PHASE-3]` Auto-moderation on uploads and bios — photos: Cloudinary moderation add-on (or AWS Rekognition fallback) flags explicit/violent content → set `pending_review`, hide from discover until admin approves; bios: OpenAI moderation endpoint on create/update → `pending_review` if flagged; usernames: `better-profanity` filter at signup; admin queue endpoint for pending content | Backend Agent + Frontend Agent | Medium | 2026-06-03 |
| P3FT.6 | `[PHASE-3]` Match email notifications — on mutual match, send both users a SendGrid email with: match preview (name, photo, 1-2 lifestyle tags), deep link to chat, unsubscribe link; `emailOnMatch` user preference toggle (default true); respect SendGrid 100/day free-tier cap with graceful fallback | Backend Agent | Medium | 2026-06-03 |
| P3FT.7 | `[PHASE-3]` Admin audit log — immutable append-only `admin_audit_log` collection; fields: timestamp, adminUserId, action, targetUserId, targetResourceId, reason, ipAddress; every admin endpoint writes an entry before returning; `GET /admin/audit-log` (admin-only, paginated); no update/delete endpoints | Backend Agent + Frontend Agent | Medium | 2026-06-03 |

#### Email Notifications (requires P3FT.2 SendGrid setup)

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
| P3EM.1 | `[PHASE-3]` Email: match created — send email to both users when a mutual match is confirmed; include match preview (name, photo, 1–2 lifestyle tags) and deep link to chat; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |
| P3EM.2 | `[PHASE-3]` Email: like received — send email to recipient user when someone likes them; optional and potentially noisy; recommend an `emailOnLike` user preference toggle (default false); depends on P3FT.2 (SendGrid) | Backend Agent | Low | 2026-06-04 |
| P3EM.3 | `[PHASE-3]` Email: account deletion confirmation — send user a "your account has been scheduled for deletion, restore within 7 days at [link]" email on soft-delete; currently the restore token is returned in the API response body only; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |
| P3EM.4 | `[PHASE-3]` Email: account deactivation confirmation — send user a "your account is deactivated; reactivate within 30 days before it is permanently deleted" email on deactivation; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |
| P3EM.5 | `[PHASE-3]` Email: account pause confirmation — send user a brief "your profile is now paused and hidden from discover" confirmation; optional, low priority; depends on P3FT.2 (SendGrid) | Backend Agent | Low | 2026-06-04 |
| P3EM.6 | `[PHASE-3]` Email: password reset token — currently the plain reset token is returned in the `POST /api/auth/forgot-password` response body (dev/MVP mode); replace with SendGrid delivery so the token is emailed to the user in production; depends on P3FT.2 (SendGrid) | Backend Agent | High | 2026-06-04 |
| P3EM.7 | `[PHASE-3]` Email: account restored after soft-delete — send user a "welcome back, your account has been restored" email on successful `POST /api/auth/restore-account`; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |
| P3EM.8 | `[PHASE-3]` Email: admin alert when a user is banned — notify admin email list when `POST /api/admin/ban/{user_id}` is called, including triggering admin ID, banned user ID/username, and timestamp; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |
| P3EM.9 | `[PHASE-3]` Email: admin alert when a conversation report is filed — notify admin email list when `POST /api/chat/{partner_id}/report` is submitted, including reporter/reported usernames and report reason; depends on P3FT.2 (SendGrid) | Backend Agent | Medium | 2026-06-04 |

---

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
| P3T.2 | `[PHASE-3]` Add notification creation tests — like-received and match-created events should trigger notifications | Tests Agent | Medium | 2026-05-29 |
| P3T.3 | `[PHASE-3]` Add gender-gate test — users should only see same-gender recommendations | Tests Agent | Medium | 2026-05-29 |
| P3T.4 | `[PHASE-3]` Add MAX_MATCHES cap test — enforce that 5-match limit is respected | Tests Agent | Medium | 2026-05-29 |
| P3T.5 | `[PHASE-3]` Add Vitest + React Testing Library — at minimum test `AuthContext`, `api.js`, and the like/match UI flow | Tests Agent | High | 2026-05-29 |
| P3T.6 | `[PHASE-3]` Add tests for cluster/recommendation algorithm internals | Tests Agent | Low | 2026-05-29 |
| P3T.7 | `[PHASE-3]` Convert `test_api.py` and `test_api_v2.py` from plain Python scripts to proper pytest modules | Tests Agent | Low | 2026-05-29 |

#### Admin Dashboard

| ID | Task | Owner | Priority | Added |
|----|------|-------|----------|-------|
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
| P4.2 | `[PHASE-4]` Lawyer review of Privacy Policy and Terms of Service — the beta versions were drafted programmatically and cover standard clauses; have a lawyer review before campus-wide launch to ensure FERPA compliance (student data), COPPA compliance (age verification), and enforceability of the arbitration/dispute clauses | — | High | 2026-06-03 |
