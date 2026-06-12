# RoomMatch — Codebase Improvement Plan

Generated 2026-06-11 from a full scan of `backend/`, `frontendv2/`, `frontendAdmin/`, and `frontend/`.
No changes have been made — this is a planning document only.

Items are ordered **largest change first**. Each has a size rating:
**XL** (multi-day / architectural) · **L** (a day or so) · **M** (a few hours) · **S** (under an hour).

---

## XL — Architectural

### 1. Replace the O(N²) full-recompute recommendation pipeline
Every registration (`authRoutes.py:177-185`), profile update (`userRoutes.py:122-127`), user creation (`userRoutes.py:92-97`), and unmatch (`userRoutes.py:238-242`) calls `RecommendationService.on_new_user`/`on_user_unmatched`, which **recomputes recommendations for every user against every other user, serially, inside the request** (`recommendationService.py:48-52`). With N users that's N × N score computations plus N DB writes per signup. This works for a demo but will visibly stall requests at a few hundred users.
- Move recomputation out of the request path (background task via `asyncio.create_task`, a job queue, or a periodic batch).
- For a single new/updated user, only recompute *that user's* list plus incremental insertion into others' lists — not a full N² sweep.
- `ClusterService` (`clusterService.py`) already exists for candidate narrowing but is **never used anywhere** — either wire it in to cut the candidate pool or delete it.

### 2. Make match creation atomic (race conditions in `likeService.send_like`)
`likeService.py:36-160` enforces `MAX_MATCHES` and builds `matchedWith` via read-modify-write across multiple awaits. Two simultaneous mutual likes can: exceed `MAX_MATCHES`, create duplicate `matches` documents, or write inconsistent `matchedWith`/`matchCount` between the two users. The "re-fetch for fresh data" at line 87 narrows but does not close the window.
- Use MongoDB transactions (Motor supports them on replica sets) or single-document atomic guards (`$addToSet` + `$size`-conditioned filter like `{"matchCount": {"$lt": MAX_MATCHES}}` in the update filter).
- Also dedupe the `matches` collection with a unique index on a canonical `(min(id), max(id))` pair — `migrate_indexes.py:47` creates `matches_pair` but **not unique**, and pairs are stored in either order.
- Related: `matchedWith` arrays, `matchCount`, and the `matches` collection are three copies of the same fact that are manually kept in sync in 5+ places (`likeService`, `blockService`, `deletionService`, `userProfileService`). Deriving everything from the `matches` collection would remove an entire class of consistency bugs (and the `_normalize_matched_with` helper duplicated in 4 files).

### 3. Remove the legacy `frontend/` React Native app — and its committed `node_modules`
**24,784 of the repo's 27,773 tracked files (89%) are `frontend/node_modules/`** committed to git. The Expo/React Native app in `frontend/` duplicates `frontendv2` feature-for-feature and doesn't match the CLAUDE.md architecture (which documents only `frontendv2`). If it's dead, delete the directory; if it must stay, at minimum `git rm -r --cached frontend/node_modules` and gitignore it. This single change will dramatically shrink clone size and repo noise. (Consider whether git history rewriting is worth it; likely not necessary.)

---

## L — Significant features / refactors

### 4. Fix the broken Block/Unblock frontend–backend contract (currently a dead feature)
Backend `POST /users/{user_id}/block` (`userRoutes.py:348-359`) expects `{user_id}` = **the blocker** (enforced by `get_current_user_or_403`) and a body `{"userId": <blocked_id>}`. The frontend (`frontendv2/src/services/api.js:103-104`) calls `api.post('/users/<TARGET>/block')` — target ID in the path, **no body**. Result: every Block click from `UserDetailPage.jsx:82` returns **403 Forbidden**, and every Unblock from `ProfilePage.jsx:184` likewise fails. Tests pass because they exercise the backend contract directly. Fix the api.js signatures (`blockUser(currentUserId, targetId)`) and their call sites, and add an end-to-end check.

### 5. Enforce ban / soft-delete / deactivation at the auth layer
`get_current_user` (`auth/dependencies.py:10-26`) only checks the user exists. Consequences:
- A **banned** user keeps full API access for up to 24h (token lifetime) and can then call `/auth/refresh` (`authRoutes.py:221-236`), which has **no ban check**, to mint fresh tokens indefinitely. Ban is only enforced at password login.
- A **soft-deleted** user (`deletedAt` set) can likewise keep using the app during the grace period with their old token.
Add `is_banned` / `deletedAt` checks in `get_current_user` and in `/auth/refresh`. There are already tests for ban behavior — extend them.

### 6. Stop returning every user's email/DOB/private fields to any logged-in user
`GET /users/all` (`userRoutes.py:70-79`) and `GET /users/{id}` (`userRoutes.py:106-112`) return the **raw user document minus only `_id` and `hashed_password`** — including `email`, `dateOfBirth`, `termsVersion`, `is_paused`, refresh-token expiry timestamps, restore-token hashes, etc., to any authenticated user. `UserResponse` even declares `email` as a field. Build a public-profile projection (username, bio, photo, gender, tags, preference scores) and use it for all non-self, non-admin reads. Also question whether `/users/all` (full user dump, 60/min) should exist at all for non-admins — discover only needs `/top-matches`.

### 7. Replace 3-second chat polling with something cheaper (or smarter)
`ChatPage.jsx:91-97` polls full message history **and** writes a `mark-read` upsert every 3 seconds per open chat; `NotificationBell` and unread-chat checks add more polling. Backend `get_unread_chats` (`userRoutes.py:529-554`) then does one `find_one` + one `count_documents` **per partner per call**. Options in increasing ambition: (a) only fetch messages after the latest known timestamp (the dead `chatRoutes.py` already sketched an `after` param), and only `mark-read` when new partner messages actually arrived; (b) move unread counting to a single aggregation; (c) WebSockets/SSE for push. Even just (a)+(b) cuts DB load by an order of magnitude.

### 8. Eliminate N+1 query patterns on the backend
Recurring pattern of per-item `find_one` in async loops:
- `get_conversations` (`chatService.py:58-85`) — one query per match partner; use one aggregation over `chat_messages`.
- `admin_user_activity` (`userRoutes.py:734-798`) — `get_username` does a `find_one` per row, plus loads *all* messages into memory to count them; use `$in` lookups and an aggregation for counts.
- `admin_get_feedback` (`userRoutes.py:862-872`) and `admin_get_conversation_reports` (`userRoutes.py:909-922`) — `find_one` per item for usernames.
- `blockService.get_blocked_by_user` (`blockService.py:96-109`) — `find_one` per blocked ID; use `{"id": {"$in": ids}}`.

### 9. Eliminate N+1 fetches on the frontend
- `DiscoverPage.jsx:28-33` — `getUser()` per recommended match (10 extra requests per page load). Have `/top-matches` return enriched profile data server-side.
- `MatchesPage.jsx:24-30` — `getUser()` **and** `getMatchScore()` per match partner. The score was already known at match time; store `compatibilityScore` on the match document (the `ConfirmedMatch` model has the field, but `likeService.send_like` never writes it) and return partners enriched.

---

## M — Medium fixes

### 10. Delete dead backend code
- `app/routers/chatRoutes.py` — **not mounted in main.py**; also calls `chatService.get_messages(..., after=...)` with a kwarg that doesn't exist, so it would crash if ever mounted.
- `app/routers/matchRoutes.py` — not mounted; in-memory `userStore`, **no auth on any endpoint**. Dangerous if anyone ever mounts it.
- `app/services/userProfiles.py` — imports `User` from `app.models`, which doesn't exist → ImportError on import; clearly dead.
- `app/services/clusterService.py` — never imported by live code (see item 1; use it or remove it).
- `UserProfileService.get_next_id` (`userProfileService.py:8-21`) — max+1 ID generation with a read/write race; the atomic `counters` approach in `authRoutes._get_next_id` is correct. `create_user` (used by `POST /users` and `/uploadUsers`) still uses the racy version — unify on the counter.
- `UserProfileService.mark_matched` / `unmatch_user` (`userProfileService.py:199-245`) — legacy single-match logic (`matchedWith: int`), unused by routes.
- Duplicated `UPLOAD_DIR` setup in both `main.py:213` and `userRoutes.py:578`.

### 11. Fix per-user rate limiting — it's currently one global bucket
`limiter.py:18-23` keys authenticated requests on `auth[7:39]` — the first 32 characters of the JWT. For HS256 tokens from python-jose, those characters are the **base64 header, identical for every user** (`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…`). All authenticated users therefore share a single rate-limit bucket: one active user can 429 everyone on a shared deployment. Decode the token's `sub` (the helper `_user_id_from_request` in `main.py:54` already does this) or key on a hash of the *whole* token. Also note `_build_storage_uri` silently falls back to `memory://` (per-process limits) when only Upstash REST creds are present.

### 12. Don't leak internal exception text in 500 responses; remove `except Exception` + `pass` anti-pattern
`userRoutes.py:102-104` and `181-183` do `except Exception as e: pass; raise HTTPException(500, detail=str(e))` — the `pass` is dead, and `str(e)` can expose DB/internal details to clients. Several other broad `except Exception: pass` blocks (registration recompute `authRoutes.py:184-185`, startup cleanup `main.py:123-140`, `get_likes_received` auto-match `likeService.py:194-195`) swallow errors with no logging — at minimum log them; Sentry is already wired up.

### 13. Run blocking work off the event loop
- `cloudinary.uploader.upload` / `.destroy` are **synchronous HTTP calls** made directly inside async endpoints (`userRoutes.py:660,671`; `deletionService.py:191`) — they block the entire server while uploading. Wrap in `run_in_executor` / `asyncio.to_thread`.
- Pillow re-encode (`_reencode_image`) and `bcrypt.hashpw` (cost 12, ~250ms) similarly block the loop on every register/login/password change.

### 14. Fix `get_messages` returning the *oldest* N messages
`chatService.py:42-49` sorts `createdAt` ascending then applies `limit` — once a conversation exceeds the limit, users see the oldest 100 messages and **new messages never appear**. Sort descending, limit, then reverse in memory (and ideally add `after`-timestamp pagination, see item 7).

### 15. Move scheduled cleanup out of app startup
Hard-deletion of expired soft-deletes and stale deactivated accounts runs **only in `lifespan`** (`main.py:117-140`) — i.e., only when the server restarts. A long-lived deployment never purges. Run these on a periodic timer (simple `asyncio` loop task or external cron hitting an admin endpoint). The deactivated-account purge also **hard-deletes only the user doc** via `delete_many`, skipping the full cascade that `DeletionService.hard_delete_user` does (chats, likes, blocks, Cloudinary photo, partners' `matchedWith`) — leaving orphaned data.

### 16. Validate the newer profile fields server-side
`religionTag`, `major`, `graduationSeason`, `graduationYear` (`authRoutes.py:40-43`, `models.py:30-33`) have **no max length, no allowed-value checks, and no HTML sanitization** — unlike `bio`/`lifestyleTags` which are carefully sanitized with nh3. Free-text `religionTag` of unbounded size is storable and is rendered on other users' screens. Mirror the lifestyle-tags approach (server-side allowlists matching the frontend option lists in `App.jsx` / `SignupPage`).

### 17. Tighten `Preference` validation per category
`Preference.value` allows 0–24 for *every* category (`models.py:16-18`) because sleep shares the model. A client can submit `cleanliness: 24` on a 0–10 scale; `preferenceScore` then computes a negative score ((24-0)/10)² = 5.76 → score −4.76) that pollutes averages instead of clamping. Use per-field validators or two Preference types (0–24 sleep, 0–10 others).

### 18. Question the `POST /users` profile-creation endpoint
`userRoutes.py:81-104` lets **any authenticated user create unlimited password-less profile documents** (no email, no age check, no ToS) — bypassing registration's safeguards entirely. It appears to be a leftover from pre-auth days (tests/admin seeding). Restrict to admin, or remove it and seed via `/uploadUsers` (which is already admin-gated).

---

## S — Small fixes

### 19. `forgot-password` returns the reset token to the caller
`authRoutes.py:285-305` — anyone who knows a victim's email receives that account's password-reset token directly in the HTTP response → full account takeover. The code comments acknowledge it's an MVP stopgap pending email delivery, and the dual-response shape already exists; until email sending lands, this endpoint should be disabled in production or gated behind an env flag. **The highest-severity finding in the scan despite being a small change.** (Same pattern: `DELETE /users/{id}` returns the restore token in-band, but there it's returned to the account owner, which is acceptable.)

### 20. Sleep-schedule scoring isn't circular
`matchScore.py` treats `sleepScheduleWeekdays` as a linear 0–24 value, so bedtimes of 23:00 and 01:00 score as 22 hours apart (maximum mismatch / instant deal-break) when they're really 2 hours apart. Use circular distance: `min(d, 24 - d)`.

### 21. `guests` deal-breaker can never trigger
`categoryRange["guests"] = [10, 1.0]` (`matchScore.py:10`) → deal-break threshold is `10 × 1.0 = 10`, but max possible difference is 10 and the check is strictly `>`. If intentional ("guests can't be a deal-breaker"), document it; the UI still offers the toggle, which silently does nothing.

### 22. `compatibilityScore` double-computes and double-checks
`compatibilityScore` (`matchScore.py:52-56`) calls `matchScore(u1,u2)` and `matchScore(u2,u1)` — but both the per-category deal-break check and `preferenceScore` are **symmetric** (`abs` of the same pair), so the two calls always return identical values and `genderCompatible` runs 3×. Either the function collapses to a single `matchScore` call, or the asymmetry that `min()` was meant to capture never got implemented.

### 23. Inconsistent timestamp handling
`datetime.utcnow().isoformat()` (naive string) is used for `termsAcceptedAt`, feedback, and conversation reports (`userRoutes.py:475,856,903`; `authRoutes.py:163`) while everything else uses `datetime.now(timezone.utc)` (aware datetime). `utcnow()` is deprecated in Python 3.12+, and string-vs-datetime mixing breaks `$gt`/sorting. The frontend already compensates for missing `Z` suffixes (`ChatPage.jsx:12`). Standardize on aware datetimes.

### 24. `markChatRead` and duplicate helpers — frontend tidy-ups
- `api.js:156` — `markChatRead(userId, partnerId)` ignores `userId`; drop the parameter.
- `ChatPage.jsx:10-32` — `formatMessageTime` and `formatSeenTime` are byte-identical functions; keep one.
- `App.jsx` is 601 lines and `ProfilePage.jsx` 768 — extract `AgeGateModal`, `TermsModal`, profile-completion prompt, and option-list constants (`MAJOR_OPTIONS` etc., which must stay in sync with backend validation per item 16) into shared modules.

### 25. Side effects in GET handlers
`get_likes_received` (`likeService.py:162-200`) silently **creates matches** during a read (auto-resolving mutual likes), with failures swallowed by `except Exception: pass`. Mutual likes should be resolved at like time (`send_like` already handles the stale-mutual case); the GET should be read-only. Lower surprise, fewer hidden writes.

### 26. Missing rate limits on a few endpoints
`/matchScore` and `/match` (`matchingRoutes.py:23-74` — `/match` runs an O(N²) graph matching over all users on demand, a cheap DoS), `/auth/me`, `/admin/ban`, `/admin/unban`, and `/uploadUsers` have no `@limiter.limit`. Also consider whether `/match` (full pairing of the entire user base, returns all user IDs) should be admin-only — currently any logged-in user can call it.

### 27. Committed user photos
`backend/uploads/photos/*.jpg` (real user-uploaded images) are tracked in git. Legacy local uploads are intentionally retained for serving, but they shouldn't live in version control — gitignore the directory and rely on deployment persistence (or finish migrating the legacy users to Cloudinary and drop local serving).

### 28. Misc
- `auth/utils.py:40` — comment says "no refresh flow; users must re-login" but a refresh flow exists; stale comment.
- Single refresh token per user (`refresh_token_hash` overwritten on each login, `authRoutes.py:93-102`) — logging in on a second device silently kills the first device's session. Acceptable MVP behavior; document or move to a tokens collection.
- `BodySizeLimitMiddleware` (`main.py:89-103`) trusts `Content-Length` only — chunked requests bypass it. Defense-in-depth concern; the 5MB explicit check in upload remains the real guard.
- `_detect_image_type` (`userRoutes.py:589-597`) will IndexError on a 0-byte upload (`data[:3]` is fine, but a fully empty body still flows into Pillow paths) — verify empty-file handling.
- Cloudinary public-ID extraction by URL string-splitting (`userRoutes.py:659`, `deletionService.py:190`) breaks if assets are ever uploaded into folders; store `public_id` on the user doc at upload time instead.

---

## Questionable implementations (flagged, decision needed)

| # | Location | Concern |
|---|----------|---------|
| Q1 | `authRoutes.py:285` | Password-reset token returned in API response — account takeover until email delivery exists (item 19). |
| Q2 | `frontendv2 api.js:103` / `userRoutes.py:348` | Block/unblock is wired up but cannot succeed — has this feature ever worked in production? (item 4). |
| Q3 | `dependencies.py:10` + `authRoutes.py:221` | Banned/soft-deleted users retain access via existing or refreshed tokens (item 5). |
| Q4 | `userRoutes.py:70,106` | All users' emails/DOBs visible to any authenticated user (item 6). |
| Q5 | `limiter.py:21` | Per-user rate limiting is actually one shared global bucket (item 11). |
| Q6 | `userRoutes.py:81` | Authenticated users can create unlimited password-less profiles bypassing age/ToS gates (item 18). |
| Q7 | `likeService.py:162` | GET endpoint that creates matches as a side effect (item 25). |
| Q8 | `matchScore.py` | Sleep distance not circular; `guests` deal-breaker unreachable; `min()` of two identical symmetric scores (items 20–22). |
| Q9 | `main.py:125-140` | Deactivated-account purge hard-deletes user docs *without* the cascade used everywhere else — orphans chats/likes/blocks and partners' `matchedWith` (item 15). |
| Q10 | repo root | 89% of tracked files are `frontend/node_modules`; real user photos committed (items 3, 27). |
| Q11 | `userRoutes.py:420-454` | `submit-age` instantly bans on under-18 input — a single date-picker typo permanently locks the account with no appeal path. Consider a confirm step or admin-reversible state. |
| Q12 | `recommendationService.py` / `userRoutes.py:148-168` | Recommendations are precomputed top-10, then filtered at read time by blocks/skips/paused — a user who skips/blocks a few candidates can end up with an empty discover page even though compatible users exist, until something triggers a recompute. |

---

## Suggested sequencing

1. **Security/correctness quick wins first (S):** items 19, 11, 5, 12 — small diffs, high impact.
2. **Broken feature:** item 4 (block/unblock).
3. **Repo hygiene:** items 3, 10, 27 — pure deletions, zero behavioral risk.
4. **Privacy:** item 6.
5. **Performance under growth:** items 1, 2, 7, 8, 9 — schedule as capacity allows.
