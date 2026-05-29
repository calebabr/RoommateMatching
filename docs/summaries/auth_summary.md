# Authentication Agent Summary

## Current State

Full JWT-based authentication is implemented end-to-end:
- Passwords are hashed with bcrypt (`bcrypt` library) in `backend/app/auth/utils.py`
- Tokens are HS256 JWTs (via `python-jose`) with a 24-hour expiry, signed with `SECRET_KEY` from the environment (falls back to `"roommatch-dev-secret-change-in-prod"` if unset)
- A `get_current_user` FastAPI dependency (`auth/dependencies.py`) uses `HTTPBearer` to extract and validate bearer tokens
- Auth endpoints (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`) exist in `authRoutes.py` and are registered in `main.py`
- Every route in `userRoutes.py` carries `Depends(get_current_user)` — all user/match/chat endpoints are protected
- The Axios client in `api.js` stores the JWT in `localStorage` under `token`, attaches `Authorization: Bearer <token>` to all requests via a request interceptor, and clears the token + redirects to `/login` on any 401 via a response interceptor
- `AuthContext.jsx` rehydrates state on load by calling `/auth/me` with the stored token, and exposes `login`, `signup`, `logout`, and `refreshUser`

## Key Files

| File | Role |
|------|------|
| `backend/app/auth/utils.py` | bcrypt hashing, JWT create/decode |
| `backend/app/auth/dependencies.py` | `get_current_user` dependency |
| `backend/app/routers/authRoutes.py` | register/login/me endpoints |
| `backend/app/main.py` | router registration, CORS config |
| `frontendv2/src/services/api.js` | Axios instance, token helpers, interceptors |
| `frontendv2/src/context/AuthContext.jsx` | React auth state, rehydration, login/logout |

## Gaps / TODOs

- Hardcoded fallback `SECRET_KEY` will be used in production if the env var is not set
- No token refresh mechanism — expiry forces full re-login
- CORS set to `allow_origins=["*"]` — needs to be locked down for production
- No email verification on registration
- No rate limiting on login/register (brute-force risk)
- Sequential integer user IDs are more enumerable than UUIDs
- Frontend protected-route guarding (PrivateRoute pattern) not confirmed

## Notable Decisions

- `hashed_password` is explicitly stripped from all response payloads in both `authRoutes.py` and `dependencies.py`
- A unique sparse index on `email` is created at startup — database-level duplicate guard on top of the application-level 409 check
- The 401 interceptor in `api.js` handles stale-token cleanup globally, so individual components don't need to handle it
