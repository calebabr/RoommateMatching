# Backend Summary — RoomMatch

## 1. Current State

The FastAPI backend is fully functional with auth, user CRUD, matching, likes/unmatching, chat, notifications, and photo upload. Three routers are mounted under `/api`. Auth uses JWT (HS256, 24-hour expiry) via `python-jose` and `bcrypt`. All DB operations are async via Motor. A legacy in-memory router (`matchRoutes.py`) exists but is not mounted in `main.py`.

## 2. Key Files

| File | Role |
|------|------|
| `app/main.py` | App entry point — registers routers, CORS (allow-all), static file mount for `/uploads` |
| `app/database.py` | Motor client — defines all 7 MongoDB collections |
| `app/models.py` | All Pydantic models: users, likes, matches, recommendations, chat, notifications |
| `app/auth/utils.py` | JWT creation/decoding, bcrypt password hashing |
| `app/auth/dependencies.py` | `get_current_user` FastAPI dependency (Bearer token extraction) |
| `app/routers/authRoutes.py` | Register, login, and `/auth/me` endpoints |
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
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET  /api/auth/me`

**Matching** (`/api`)
- `POST /api/matchScore`
- `POST /api/uploadUsers`
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
- `POST /api/admin/recompute`

**Utility**
- `GET  /` — health/version
- `GET  /health`

## 4. Gaps / TODOs

- **`chatRoutes.py` not mounted** — a second chat router exists with `after` timestamp pagination but is not registered in `main.py`, so that feature is unreachable.
- **`matchRoutes.py` not mounted** — the legacy in-memory router is dead code.
- **`clusterService.py` not wired** — cluster logic exists but has no router or caller.
- **`userProfiles.py` likely stale** — appears to be an older version of `userProfileService.py`; should be audited or deleted.
- **`userProfileService.mark_matched` / `unmatch_user`** — these methods use the old single-int `matchedWith` format (not the list format) and are no longer called; they are stale.
- **CORS is open** — `allow_origins=["*"]` is fine for dev but needs tightening for production.
- **`SECRET_KEY` hardcoded fallback** — `"roommatch-dev-secret-change-in-prod"` in `auth/utils.py` needs an env var enforced in prod.
- **No per-notification mark-read route exposed** — `NotificationService.mark_read()` exists but has no endpoint.
- **`/api/users` (POST) requires auth** — profile creation is auth-gated, so new users must register via `/api/auth/register` first, then separately create a profile; this two-step flow may confuse frontend.

## 5. Notable Patterns

- All routes require `get_current_user` (JWT Bearer) except `/auth/register` and `/auth/login`.
- Services are instantiated as module-level singletons inside each router file.
- `UserInDB.toMatchDict()` normalizes Pydantic models to plain dicts for the scoring engine.
- Recommendation recompute is triggered reactively on user create, update, and unmatch — no background job needed.
- `_normalize_matched_with()` is duplicated across `likeService.py`, `chatService.py`, and `userProfileService.py`; should be consolidated into a shared utility.
