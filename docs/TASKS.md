# RoomMatch Task Tracker

_Last updated: 2026-05-29 by Documentation Agent (B2 validation hardening complete)_

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

---

## Backlog

### Security

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Fix NOTE-1: `limit` parameter on `GET /users/{id}/chat/{partner_id}` is user-controlled with no upper bound — clamp to a max (e.g. 200) | Backend Agent | Low | 2026-05-29 |
| Fix NOTE-2: `/api/uploadUsers` bulk endpoint writes raw JSON file data to DB without Pydantic validation — deserialize through `UserCreate` model first | Backend Agent | Low | 2026-05-29 |

### Auth

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Implement token refresh mechanism (current expiry forces full re-login) | Auth Agent | Medium | 2026-05-29 |
| Lock down CORS — replace `allow_origins=["*"]` with explicit origin list for production | Auth Agent | High | 2026-05-29 |
| Add email verification on registration | Auth Agent | Medium | 2026-05-29 |
| Replace sequential integer user IDs with UUIDs to reduce enumeration risk | Auth Agent | Medium | 2026-05-29 |

### Backend

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Mount `chatRoutes.py` or remove it — alternate chat router with `after` timestamp pagination is currently unreachable | Backend Agent | Medium | 2026-05-29 |
| Remove or replace `matchRoutes.py` — legacy in-memory router is dead code | Backend Agent | Low | 2026-05-29 |
| Wire `clusterService.py` to a router, or remove it — cluster logic is currently unused | Backend Agent | Low | 2026-05-29 |
| Audit and delete `userProfiles.py` — likely stale duplicate of `userProfileService.py` | Backend Agent | Low | 2026-05-29 |
| Remove or update `userProfileService.mark_matched` / `unmatch_user` — use old single-int `matchedWith` format and are no longer called | Backend Agent | Low | 2026-05-29 |
| Expose per-notification mark-read endpoint — `NotificationService.mark_read()` exists but has no route | Backend Agent | Low | 2026-05-29 |
| Consolidate `_normalize_matched_with()` — duplicated across `likeService.py`, `chatService.py`, `userProfileService.py` | Backend Agent | Low | 2026-05-29 |

### Database

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Add indexes on high-traffic query fields: `users.id`, `likes.fromUser/toUser`, `matches.user1_id/user2_id`, `notifications.toUser`, `recommendations.userId`, `chat_messages.fromUser/toUser` | DB Agent | High | 2026-05-29 |
| Fix non-atomic ID generation in `get_next_id()` — races under concurrent registrations; replace with counter collection or `$inc`+`findAndModify` | DB Agent | High | 2026-05-29 |
| Enforce `matchedWith` schema — remove the three `_normalize_matched_with()` workarounds with a proper migration | DB Agent | Medium | 2026-05-29 |
| Write `compatibilityScore` into `matches` documents — `ConfirmedMatch` model has the field but `likeService` never populates it | DB Agent | Low | 2026-05-29 |
| Add TTL index on `notifications` to auto-expire old records | DB Agent | Low | 2026-05-29 |
| Add TTL index on `likes` to expire stale pending likes | DB Agent | Low | 2026-05-29 |
| Evaluate `clusters` collection — written by `clusterService` but never read for matching; either integrate or remove | DB Agent | Low | 2026-05-29 |

### Tests

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Write unit tests for `matchScore.py` in isolation (weight calculations, boundary values, multiple simultaneous dealbreakers) | Tests Agent | High | 2026-05-29 |
| Add notification creation tests — like-received and match-created events should trigger notifications | Tests Agent | Medium | 2026-05-29 |
| Add gender-gate test — users should only see same-gender recommendations | Tests Agent | Medium | 2026-05-29 |
| Add MAX_MATCHES cap test — enforce that 5-match limit is respected | Tests Agent | Medium | 2026-05-29 |
| Add tests for cluster/recommendation algorithm internals | Tests Agent | Low | 2026-05-29 |
| Add test for token invalidation behavior on logout (blocked by missing logout endpoint) | Tests Agent | Low | 2026-05-29 |
| Convert `test_api.py` and `test_api_v2.py` from plain Python scripts to proper pytest modules | Tests Agent | Low | 2026-05-29 |

### Frontend

| Task | Owner | Priority | Added |
|------|-------|----------|-------|
| Replace polling-based chat with WebSocket or SSE | Frontend Agent | Medium | 2026-05-29 |
| Implement password reset / forgot-password flow | Frontend Agent | Medium | 2026-05-29 |
| Add email verification step to signup flow | Frontend Agent | Medium | 2026-05-29 |
| Fix `UserDetailPage` like button — uses stale `profile.matched` flag; should check current user's match state | Frontend Agent | Medium | 2026-05-29 |
| Add pagination to discover, likes, matches, and chat history | Frontend Agent | Medium | 2026-05-29 |
| Stop `NotificationBell` polling when user is already on the Notifications page | Frontend Agent | Low | 2026-05-29 |
| Expose backend URL setting from within the app (not just login screen) | Frontend Agent | Low | 2026-05-29 |
| Expand gender options beyond binary male/female in `SignupPage` | Frontend Agent | Low | 2026-05-29 |
| Add Vitest + React Testing Library — at minimum test `AuthContext`, `api.js`, and the like/match UI flow | Frontend Agent | High | 2026-05-29 |
