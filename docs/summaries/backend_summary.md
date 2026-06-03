# Backend Summary — RoomMatch

## 1. Current State

The FastAPI backend is fully functional with auth, user CRUD, matching, likes/unmatching, chat, notifications, and photo upload. Three routers are mounted under `/api`. Auth uses JWT (HS256, 24-hour expiry) via `python-jose` and `bcrypt` (`rounds=12`). All DB operations are async via Motor. A legacy in-memory router (`matchRoutes.py`) exists but is not mounted in `main.py`. Rate limiting is enforced via slowapi (`SlowAPIMiddleware`) on auth endpoints. `SECRET_KEY` is enforced — a `RuntimeError` is raised at startup if it is absent and `ROOMMATCH_ENV` is not `"test"` or `"development"`. All user-facing input fields are validated with explicit bounds and format constraints; HTML content is sanitized via `nh3`; a 1 MB body-size middleware rejects oversized requests before routing.

## 2. Key Files

| File | Role |
|------|------|
| `app/main.py` | App entry point — registers routers, CORS (origin-scoped via `FRONTEND_URL`), static file mount for `/uploads`, SlowAPIMiddleware, `BodySizeLimitMiddleware` (1 MB cap), clean 422 error handler, startup index creation |
| `app/database.py` | Motor client — defines all 7 MongoDB collections |
| `app/models.py` | All Pydantic models: users, likes, matches, recommendations, chat, notifications. Includes `ALLOWED_LIFESTYLE_TAGS` frozenset and all field-level validation constraints (see Section 5). |
| `app/auth/utils.py` | JWT creation/decoding, bcrypt password hashing (`rounds=12`), `validate_password_strength()` |
| `app/auth/dependencies.py` | `get_current_user`, `get_current_user_or_403`, `verify_match_exists`, `get_admin_user` FastAPI dependencies; `_admin_ids()` reads `ADMIN_USER_IDS` env var |
| `app/limiter.py` | slowapi `Limiter` instance; rate-limits by Bearer token prefix or IP; in-memory by default, Redis via `UPSTASH_REDIS_URL` |
| `app/routers/authRoutes.py` | Register, login, `/auth/me`, `change-password`, `forgot-password`, and `reset-password` endpoints |
| `app/routers/userRoutes.py` | User CRUD, likes, matches, chat, notifications, photo upload, admin recompute |
| `app/routers/matchingRoutes.py` | Batch match scoring (`/matchScore`, `/uploadUsers`, `/match`) |
| `app/routers/chatRoutes.py` | Alternate chat router (not mounted in `main.py`) |
| `app/routers/matchRoutes.py` | Legacy in-memory match router (not mounted in `main.py`) |
| `app/services/matchScore.py` | Weighted compatibility scoring with deal-breaker logic and gender gating |
| `app/services/matchingUsers.py` | Batch user-pair matching |
| `app/services/recommendationService.py` | Computes and stores top-10 recommendations per user in MongoDB |
| `app/services/likeService.py` | Handles likes, mutual match creation, unmatch, and recommendation cleanup |
| `app/services/chatService.py` | Message send/fetch, conversation list (match-gated) |
| `app/services/notificationService.py` | Like/match/unmatch notifications with read-state tracking |
| `app/services/userProfileService.py` | User CRUD with cascade-delete for likes, matches, recommendations |
| `app/services/userProfiles.py` | Older service file (likely superseded by `userProfileService.py`) |
| `app/services/clusterService.py` | Cluster service (present but not wired to any router) |

## 3. API Endpoints

**Auth** (`/api/auth`)
- `POST /api/auth/register` — accepts full profile payload (bio, gender, lifestyleTags, all 9 scoring fields); creates complete user document in one step
- `POST /api/auth/login`
- `GET  /api/auth/me`
- `POST /api/auth/change-password` — requires Bearer token; validates `current_password`; enforces password strength on `new_password`; rate-limited 5/hour
- `POST /api/auth/forgot-password` — accepts `email`; rate-limited 3/hour; always returns HTTP 200 (no email enumeration); returns reset token in response body (no email delivery yet — dev/MVP mode only)
- `POST /api/auth/reset-password` — accepts `token` + `new_password`; rate-limited 5/hour; validates SHA-256-hashed token + expiry stored on user document; enforces password strength; clears token fields on success

**Matching** (`/api`)
- `POST /api/matchScore`
- `POST /api/uploadUsers` — gated by `get_admin_user`; 403 for non-admin users
- `POST /api/match`

**Users** (`/api`)
- `GET  /api/users/all`
- `POST /api/users`
- `GET  /api/users/{user_id}`
- `PUT  /api/users/{user_id}`
- `DELETE /api/users/{user_id}`
- `GET  /api/users/{user_id}/top-matches`
- `POST /api/users/{user_id}/like`
- `GET  /api/users/{user_id}/likes-received`
- `GET  /api/users/{user_id}/likes-sent`
- `GET  /api/users/{user_id}/matches`
- `POST /api/users/{user_id}/unmatch/{partner_id}`
- `GET  /api/users/{user_id}/chat/conversations`
- `POST /api/users/{user_id}/chat/{partner_id}`
- `GET  /api/users/{user_id}/chat/{partner_id}`
- `GET  /api/users/{user_id}/notifications`
- `GET  /api/users/{user_id}/notifications/unread-count`
- `POST /api/users/{user_id}/notifications/mark-read`
- `POST /api/users/{user_id}/upload-photo`
- `POST /api/admin/recompute` — gated by `get_admin_user`; 403 for non-admin users
- `POST /api/admin/ban/{user_id}` — gated by `get_admin_user`; sets `is_banned: True`; 404 if not found
- `POST /api/admin/unban/{user_id}` — gated by `get_admin_user`; sets `is_banned: False`; 404 if not found
- `GET  /api/admin/users` — gated by `get_admin_user`; returns all users with `is_banned` visible; strips `hashed_password` and `_id`; rate-limited 30/minute
- `GET  /api/admin/users/{user_id}/activity` — gated by `get_admin_user`; returns `matches`, `likes_sent`, `chat_partners` lists for the given user; rate-limited 30/minute

**Utility**
- `GET  /` — health/version
- `GET  /health`

## 4. Input Validation

**Session 2026-05-29 (Task B2):** Comprehensive Pydantic validation hardening was applied to all user-facing models and request bodies.

### Field constraints added

| Model / Field | Constraint |
|---------------|-----------|
| `Preference.value` | `ge=0.0, le=10.0` |
| `UserCreate.username` (and `RegisterRequest`) | `min_length=1`, `max_length=30`, `pattern=^[A-Za-z0-9_-]+$` |
| `UserCreate.gender` (and `RegisterRequest`) | `Literal["male","female"]` |
| `UserCreate.bio` (and `RegisterRequest`) | `max_length=500` + HTML strip via `nh3` |
| `UserCreate.lifestyleTags` (and `RegisterRequest`) | `max_length=10` items + whitelist against `ALLOWED_LIFESTYLE_TAGS` (20 valid tags) |
| `ChatMessageCreate.content` | `min_length=1`, `max_length=1000` + HTML strip via `nh3` |
| `UserResponse.username` / `UserInDB.username` | `max_length=30` |
| `UserResponse.bio` / `UserInDB.bio` | `max_length=500` |
| `LoginRequest.email` / `RegisterRequest.email` | `max_length=254` |
| `LoginRequest.password` / `RegisterRequest.password` | `max_length=128` |
| `ChangePasswordRequest` (both fields) | `max_length=128` |

### Middleware and error handling

- `BodySizeLimitMiddleware` — rejects any request with `Content-Length > 1 048 576` bytes (1 MB) with HTTP 413 before it reaches a route handler. The `/upload-photo` endpoint is exempt (it has its own size validation).
- `RequestValidationError` handler — returns `{"detail": [{"field": ..., "message": ...}]}` so clients receive field-level error messages without Pydantic's internal schema paths being exposed.

### Dependency

- `nh3==0.2.17` added to `requirements.txt` for HTML sanitization.

---

## 5. Secrets / Environment Configuration

**Session 2026-05-29 (Task B1):** A secrets audit was completed. Key outcomes:

- `MONGO_URL` and `MONGO_DB_NAME` were hardcoded in `app/database.py` and `migrate_add_auth_fields.py`; both are now read from environment variables with safe defaults (`mongodb://localhost:27017/` and `roommatch`).
- A root-level `.gitignore` was created covering `.env*`, `frontendv2/dist/`, `__pycache__/`, `node_modules/`, and `backend/uploads/`.
- `backend/.env.example` documents all required/optional env vars: `SECRET_KEY`, `MONGO_URL`, `MONGO_DB_NAME`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `MIN_PASSWORD_LENGTH`, `ROOMMATCH_ENV`, `JWT_ALGORITHM`, `JWT_EXPIRATION_HOURS`, `SENTRY_DSN`, `UPSTASH_REDIS_URL`.
- `frontendv2/.env.example` documents `VITE_API_BASE_URL`.
- `frontendv2/dist/` was removed from git tracking (`git rm --cached`).
- The default JWT `SECRET_KEY` (`"roommatch-dev-secret-change-in-prod"`) was present in 14 historical commits. It was removed in commit `530dcf5b`. **Key rotation is required before any production deployment.**
- Full audit findings are in `backend/SECURITY_SECRETS_AUDIT.md`.

**Session 2026-06-01 (Task H1):** JWT algorithm and expiration are now configurable via environment variables in `app/auth/utils.py`.

- `JWT_ALGORITHM` — defaults to `"HS256"` if unset.
- `JWT_EXPIRATION_HOURS` — defaults to `24` if unset.
- Both added to `backend/.env.example`.

## 6. CORS Configuration

**Session 2026-06-01 (Task C1):** CORS was hardened from a wildcard allow-all to an environment-driven allow-list.

- `allow_origins=["*"]` replaced with `[os.getenv("FRONTEND_URL", "http://localhost:3000")]` in `app/main.py`.
- `allow_methods` scoped to `["GET", "POST", "PUT", "DELETE", "OPTIONS"]`.
- `allow_headers` scoped to `["Content-Type", "Authorization"]`.
- `allow_credentials=True` retained for JWT cookie support.
- `FRONTEND_URL` added to `backend/.env.example` and `backend/.env` (development default: `http://localhost:3000`).
- `backend/test_cors.py` added: verifies that requests from allowed origin receive the correct CORS response headers, and that requests from a disallowed origin are rejected (no `Access-Control-Allow-Origin` header returned).

**Required before production:** Set `FRONTEND_URL` to the exact deployed frontend origin (e.g. `https://roommatch.auburn.edu`).

## 7. Security Headers

**Session 2026-06-01 (Task C2):** `SecurityHeadersMiddleware` was added to `app/main.py`, registered after `BodySizeLimitMiddleware`. It injects six HTTP security headers on every response.

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' res.cloudinary.com data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

**CSP note:** `style-src` includes `'unsafe-inline'` because the frontend uses inline styles via `utils/theme.js`. To remove it, inline styles must be migrated to CSS files first.

Test coverage: `backend/test_security_headers.py` (1 test, passing).

## 8. Admin Gating

**Session 2026-06-02 (Tasks P1.2 + P1.3):** Admin-only endpoints are now protected by a dedicated dependency.

- `_admin_ids()` in `app/auth/dependencies.py` reads `ADMIN_USER_IDS` (comma-separated integers) from the environment.
- `get_admin_user` dependency wraps `get_current_user` and raises HTTP 403 if the authenticated user's ID is not in the admin list.
- `POST /api/admin/recompute` (`userRoutes.py`) upgraded from `get_current_user` to `get_admin_user`.
- `POST /api/uploadUsers` (`matchingRoutes.py`) upgraded from `get_current_user` to `get_admin_user` — endpoint is retained (useful for seeding test data) but locked to admins.
- `ADMIN_USER_IDS=` added to `backend/.env` and documented in `backend/.env.example`.

**Required before production:** Set `ADMIN_USER_IDS` to a comma-separated list of integer user IDs that should have admin access (e.g. `ADMIN_USER_IDS=1,2`).

## 9. Password Reset

**Session 2026-06-02 (Task P1.4 — backend):** Forgot-password / reset-password flow added to `authRoutes.py`.

### New Pydantic models
- `ForgotPasswordRequest` — `email: str`
- `ResetPasswordRequest` — `token: str`, `new_password: str`

### New endpoints

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `POST /api/auth/forgot-password` | 3/hour | Looks up user by email. Generates a random token, stores its SHA-256 hash + expiry on the user document. Always returns HTTP 200 with the plain token in the response body. **No email is sent — token is returned directly (dev/MVP mode).** Constant-time response prevents email enumeration. |
| `POST /api/auth/reset-password` | 5/hour | Accepts plain token + new password. Hashes token with SHA-256, finds matching user with non-expired token. Enforces password strength via `validate_password_strength()`. Clears token fields on success. Returns 400 for invalid/expired/already-used tokens. |

### Security properties
- Email enumeration prevention: `forgot-password` always returns 200 regardless of whether the email exists.
- Tokens are stored as SHA-256 hashes on the user document; the plain token is only held in the response body (transit only).
- Token expiry is enforced server-side.
- One-time use: token fields are cleared immediately on successful reset.
- Password strength is enforced identically to register and change-password (zxcvbn score ≥ 2, min 8 chars).

### Known limitation
No email is sent. The token is returned in the API response body. This is intentional for the MVP — email delivery (SMTP / SendGrid) must be wired in before production launch.

## 10. Ban / Unban Admin Endpoints

**Session 2026-06-02 (Task P2.1):** Two new admin endpoints were added to `userRoutes.py` and the login handler in `authRoutes.py` was updated to gate banned users.

### New endpoints

| Endpoint | Behavior |
|----------|---------|
| `POST /api/admin/ban/{user_id}` | Sets `is_banned: True` on the user document; returns 404 if user not found; gated by `get_admin_user` |
| `POST /api/admin/unban/{user_id}` | Sets `is_banned: False` on the user document; returns 404 if user not found; gated by `get_admin_user` |

### Login ban check

`POST /api/auth/login` now raises HTTP 403 with `"Account has been banned"` if `is_banned` is `True` on the user document. The check occurs after password verification and before JWT issuance, so banned users receive an explicit rejection rather than a valid token.

### Files changed

| File | Change |
|------|--------|
| `app/routers/userRoutes.py` | Added `POST /api/admin/ban/{user_id}` and `POST /api/admin/unban/{user_id}` near the existing `/admin/recompute` endpoint |
| `app/routers/authRoutes.py` | Login handler checks `is_banned` field after password verification; raises HTTP 403 if true |

---

## 11. is_admin in Auth Responses + GET /api/admin/users

**Session 2026-06-02 (Task P2.2 — backend):** The login and `/me` responses now expose `is_admin` so the frontend can gate admin UI without a separate round-trip. A new admin-gated endpoint lists all users.

### Changes to `authRoutes.py`

| Change | Detail |
|--------|--------|
| `import _admin_ids` | Imported from `app.auth.dependencies` |
| Login handler | Sets `user["is_admin"] = (user["id"] in _admin_ids())` before building the JWT response |
| `/me` handler | Sets `current_user["is_admin"]` the same way before returning |

### New endpoint

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `GET /api/admin/users` | 30/minute | Admin-gated (`get_admin_user`); returns all users; strips `hashed_password` and `_id`; exposes `is_banned` |

### Files changed

| File | Change |
|------|--------|
| `app/routers/authRoutes.py` | Imported `_admin_ids`; login + `/me` set `is_admin` on response |
| `app/routers/userRoutes.py` | Added `GET /api/admin/users` near other admin endpoints |

---

## 12. Admin User Activity Endpoint

**Session 2026-06-02 (Task P3AD.3):** A new admin-gated endpoint was added to `userRoutes.py` that returns aggregated activity data for any user.

### New endpoint

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `GET /api/admin/users/{user_id}/activity` | 30/minute | Admin-gated (`get_admin_user`); returns 404 if user not found; returns three keys, all guaranteed as lists (never null) |

### Response shape

| Key | Source | Fields |
|-----|--------|--------|
| `matches` | `matches_collection` where `user1_id` or `user2_id` == user_id | `partner_id`, `partner_name`, `matched_date` (from `confirmedAt`) |
| `likes_sent` | `likes_collection` where `fromUser` == user_id | `to_user_id`, `to_user_name`, `created_at` |
| `chat_partners` | `chat_collection` aggregated across sent/received messages | `partner_id`, `partner_name`, `message_count`, `last_message_at` |

Missing partner users are surfaced as `"Deleted User"` rather than an error. All `_id` fields are excluded from output.

### Files changed

| File | Change |
|------|--------|
| `app/routers/userRoutes.py` | Added `GET /api/admin/users/{user_id}/activity` near other admin endpoints |

---

## 13. Gaps / TODOs (pre-production)

- **`chatRoutes.py` not mounted** — a second chat router exists with `after` timestamp pagination but is not registered in `main.py`, so that feature is unreachable.
- **`matchRoutes.py` not mounted** — the legacy in-memory router is dead code.
- **`clusterService.py` not wired** — cluster logic exists but has no router or caller.
- **`userProfiles.py` likely stale** — appears to be an older version of `userProfileService.py`; should be audited or deleted.
- **`userProfileService.mark_matched` / `unmatch_user`** — these methods use the old single-int `matchedWith` format (not the list format) and are no longer called; they are stale.
- **CORS is scoped** — `allow_origins` is now driven by the `FRONTEND_URL` env var (defaults to `http://localhost:3000` for development). Set `FRONTEND_URL` to the production origin before deploying.
- **No per-notification mark-read route exposed** — `NotificationService.mark_read()` exists but has no endpoint.
- **Password reset has no email delivery** — `POST /api/auth/forgot-password` returns the reset token in the response body (dev/MVP mode). SMTP or a transactional email service (SendGrid, SES, etc.) must be wired in before production launch.

## 14. Notable Patterns

- All routes require `get_current_user` (JWT Bearer) except `/auth/register` and `/auth/login`.
- Rate limiting is enforced on auth endpoints via slowapi (`app/limiter.py`): register 3/hour, login 5/15min, change-password 5/hour, forgot-password 3/hour, reset-password 5/hour. 429 responses include `Retry-After: 60`.
- Services are instantiated as module-level singletons inside each router file.
- `UserInDB.toMatchDict()` normalizes Pydantic models to plain dicts for the scoring engine.
- Recommendation recompute is triggered reactively on user create, update, and unmatch — no background job needed.
- `_normalize_matched_with()` is duplicated across `likeService.py`, `chatService.py`, and `userProfileService.py`; should be consolidated into a shared utility.
- Password strength validation (`validate_password_strength()`) uses zxcvbn (min 8 chars + score ≥ 2, configurable via `MIN_PASSWORD_LENGTH` env var) and is applied at both register and change-password.
- Sentry integration: if `SENTRY_DSN` env var is set, `sentry_sdk.init` is called with `FastApiIntegration` + `StarletteIntegration`, `traces_sample_rate=0.1` in production (0.0 otherwise), `send_default_pii=False`, and a `_before_send` hook that drops 401/403/404/429 `HTTPException` events, replaces `Authorization` header values with `"[Filtered]"`, and strips cookies. A `GET /debug/sentry-test` endpoint is registered in non-production environments to trigger a test event.
- `main.py` lifespan creates a unique sparse index on `users.email` at startup.
