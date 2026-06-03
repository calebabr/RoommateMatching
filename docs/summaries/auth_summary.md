# Authentication Agent Summary

## Current State

Full JWT-based authentication is implemented end-to-end:
- Passwords are hashed with bcrypt (`bcrypt` library) in `backend/app/auth/utils.py` with an explicit cost factor of `rounds=12` in `hash_password()`
- Tokens are HS256 JWTs (via `python-jose`) with a 24-hour expiry, signed with `SECRET_KEY` from the environment. If `SECRET_KEY` is set, it is used. If `ROOMMATCH_ENV` is `"test"` or `"development"`, the fallback `"dev-only-secret-not-for-production"` is used. Otherwise, a `RuntimeError` is raised at startup — the app will not start in production without `SECRET_KEY` set.
- A `get_current_user` FastAPI dependency (`auth/dependencies.py`) uses `HTTPBearer` to extract and validate bearer tokens. The same file also provides `get_current_user_or_403` (enforces resource ownership) and `verify_match_exists` (gates chat access to matched users only).
- Auth endpoints exist in `authRoutes.py` and are registered in `main.py`: register, login, me, and change-password (4 total).
- Every route in `userRoutes.py` carries `Depends(get_current_user)` — all user/match/chat endpoints are protected.
- Rate limiting is enforced via `SlowAPIMiddleware` (slowapi) in `main.py`. Limits: `POST /register` 3/hour, `POST /login` 5/15min, `POST /change-password` 5/hour. `/me` is unlimited. On limit hit, the response is HTTP 429 with `Retry-After: 60`.
- The Axios client in `api.js` stores the JWT in `localStorage` under `token`, attaches `Authorization: Bearer <token>` to all requests via a request interceptor, and on any 401 clears both `token` and `roommatch_user` from localStorage before redirecting to `/login`.
- `AuthContext.jsx` rehydrates state on load by calling `/auth/me` with the stored token, and exposes `user`, `token`, `loading`, `login`, `signup`, `logout`, `refreshUser`, and `setUser`. The user object is persisted to localStorage under `roommatch_user`; `saveSession`/`clearSession` manage this.
- Password strength is validated at both register and change-password via `validate_password_strength()`: enforces minimum length (default 8, configurable via `MIN_PASSWORD_LENGTH` env var) and a zxcvbn score of ≥ 2. On failure, returns HTTP 422 with a zxcvbn feedback hint.

## Key Files

| File | Role |
|------|------|
| `backend/app/auth/utils.py` | bcrypt hashing (`rounds=12`), JWT create/decode, `validate_password_strength()` |
| `backend/app/auth/dependencies.py` | `get_current_user`, `get_current_user_or_403`, `verify_match_exists` dependencies |
| `backend/app/routers/authRoutes.py` | register, login, me, change-password endpoints |
| `backend/app/main.py` | Router registration, CORS config (origin-scoped via `FRONTEND_URL`), SlowAPIMiddleware, startup index creation |
| `backend/app/limiter.py` | slowapi `Limiter` instance; keys by first 32 chars of Bearer token or IP fallback; in-memory by default, Redis via `UPSTASH_REDIS_URL` |
| `frontendv2/src/services/api.js` | Axios instance, token helpers, interceptors |
| `frontendv2/src/context/AuthContext.jsx` | React auth state, rehydration, login/logout, localStorage persistence |

## Auth Endpoints

See the updated endpoint table in the **Token Refresh** section above for the complete list including `/refresh` and `/logout`.

### `POST /api/auth/change-password`
Requires a valid Bearer token. Request body must include `current_password` (validated against the stored hash) and `new_password` (validated via `validate_password_strength()`). On success, updates the bcrypt hash in the database. Returns 401 if `current_password` is wrong, 422 if `new_password` fails strength requirements, 429 if rate limit exceeded.

## Token Refresh (P3A.1 — 2026-06-03)

A 30-day refresh token layer was added alongside the existing 24-hour access token. The full token lifecycle is now:

1. **Login / Register** — server issues both a 24h access token (JWT) and a 30d refresh token (opaque `secrets.token_urlsafe(32)`). The plain refresh token is returned in the response; its SHA-256 hash is stored on the user document alongside an expiry field (`refresh_token_hash`, `refresh_token_expires`).
2. **API requests** — access token sent as `Authorization: Bearer <token>` on every request (unchanged).
3. **Access token expiry (401)** — the queued interceptor in `api.js` pauses all in-flight requests, calls `POST /api/auth/refresh` with the stored refresh token, retries the queue with the new access token on success, or clears all tokens and redirects to `/login` on failure.
4. **Refresh token rotation** — each successful `/refresh` call generates a new refresh token; the old hash is replaced. Replaying the old token returns 401.
5. **Logout** — `POST /api/auth/logout` (Bearer-authenticated) `$unset`s `refresh_token_hash` and `refresh_token_expires` from the user document, invalidating the refresh token server-side. `AuthContext.logout()` calls this before clearing localStorage.

### New endpoints

| Method | Path | Auth Required | Rate Limit | Behavior |
|--------|------|---------------|------------|---------|
| `POST` | `/api/auth/refresh` | No (refresh token in body) | 10/hr | Validates hash + expiry; rotates token; returns new `access_token` + `refresh_token`; 401 on invalid/expired |
| `POST` | `/api/auth/logout` | Bearer token | 10/hr | Clears `refresh_token_hash` + `refresh_token_expires` on user document |

### Frontend changes

- `api.js`: `saveRefreshToken`, `loadRefreshToken`, `clearRefreshToken` (localStorage key: `roommatch_refresh_token`); `authRefresh(refreshToken)`, `authLogout()` API functions; queued 401 interceptor (`_isRefreshing` flag + `_refreshQueue`; skips refresh loop if the failing request was itself `/auth/refresh`)
- `AuthContext.jsx`: `login` and `signup` save `refresh_token` from response; `logout` is async and calls `authLogout()` before clearing localStorage

### Known gap

No database index on `refresh_token_hash`. A sparse index should be added before production (future DB agent task).

---

## Auth Endpoints (updated — includes refresh and logout)

| Method | Path | Auth Required | Rate Limit |
|--------|------|---------------|------------|
| `POST` | `/api/auth/register` | No | 3/hour |
| `POST` | `/api/auth/login` | No | 5/15min |
| `GET`  | `/api/auth/me` | Bearer token | None |
| `POST` | `/api/auth/change-password` | Bearer token | 5/hour |
| `POST` | `/api/auth/forgot-password` | No | 3/hour |
| `POST` | `/api/auth/reset-password` | No | 5/hour |
| `POST` | `/api/auth/refresh` | No (refresh token in body) | 10/hour |
| `POST` | `/api/auth/logout` | Bearer token | 10/hour |

---

## Gaps / TODOs

- ~~No token refresh mechanism~~ — resolved in P3A.1 (2026-06-03)
- No index on `refresh_token_hash` field — add sparse index via DB agent
- CORS is now scoped to the `FRONTEND_URL` env var (defaults to `http://localhost:3000`); set this to the production frontend origin before deploying
- No email verification on registration
- Sequential integer user IDs are more enumerable than UUIDs

## Notable Decisions

- `hashed_password` is explicitly stripped from all response payloads in both `authRoutes.py` and `dependencies.py`
- `users.email` unique sparse index is created at startup in `main.py` lifespan — database-level duplicate guard on top of the application-level 409 check
- The 401 interceptor in `api.js` handles stale-token cleanup globally (both `token` and `roommatch_user`), so individual components do not need to handle it
- `app/limiter.py` optionally reports rate limit violations to Sentry (as warnings with route, IP, and user ID) when `SENTRY_DSN` is set
