# RoomMatch Database Summary

## 1. Current State

Motor (`AsyncIOMotorClient`) connects to `mongodb://localhost:27017/` using database `roommatch`. Seven collections are referenced as module-level globals in `database.py`:

| Variable | Collection |
|---|---|
| `users_collection` | `users` |
| `likes_collection` | `likes` |
| `matches_collection` | `matches` |
| `recommendations_collection` | `recommendations` |
| `clusters_collection` | `clusters` |
| `chat_collection` | `chat_messages` |
| `notifications_collection` | `notifications` |
| `counters_collection` | `counters` |

One index is declared: `main.py` lifespan creates a unique sparse index on `users.email` at startup via `users_collection.create_index("email", unique=True, sparse=True)`. All other collections remain unindexed.

## 2. Schema Overview

**users** — Core profile. Key fields: `id` (int), `username`, `email`, `hashed_password`, `gender` ("male"/"female"), `matched` (bool), `matchCount` (int), `matchedWith` (list[int]), `bio`, `photoUrl`, `lifestyleTags` (list[str]), `createdAt`, plus nine preference sub-documents each with `{value: float, isDealBreaker: bool}`: `sleepScoreWD`, `sleepScoreWE`, `cleanlinessScore`, `noiseToleranceScore`, `guestsScore`, `personalityScore`, `smokingScore`, `sharedSpaceScore`, `communicationScore`.

**likes** — Pending (unreciprocated) likes. Fields: `fromUser` (int), `toUser` (int), `createdAt`. Records are deleted once a mutual match forms.

**matches** — Confirmed mutual matches. Fields: `user1_id` (int), `user2_id` (int), `confirmedAt`. No `compatibilityScore` is stored (model defines it but `likeService` omits it on insert).

**recommendations** — Top-N scored candidates per user. Fields: `userId` (int), `matches` (list of `{user_id, compatibilityScore}`), `computedAt`. Upserted on every recompute.

**clusters** — K-means cluster assignments. Fields: `userId` (int), `clusterId` (int). Upserted per user.

**chat_messages** — Direct messages between matched users. Fields: `fromUser` (int), `toUser` (int), `content` (str), `createdAt`.

**notifications** — Activity alerts. Fields: `type` ("like_received" | "match_created" | "unmatch"), `fromUser` (int), `toUser` (int), `message` (str), `read` (bool), `createdAt`.

## 3. Query Patterns

- All lookups use the custom integer `id` field (`find_one({"id": user_id})`), not MongoDB's `_id`.
- `_id` is always stripped before returning documents to callers; notifications and chat messages convert `_id` to a string `id`.
- Next user ID is generated atomically via `find_one_and_update` with `$inc` on the `counters` collection (`upsert=True`, `ReturnDocument.AFTER`). On first startup, `main.py` lifespan seeds the counter from the current max user ID using `$setOnInsert`, preserving existing IDs.
- Bidirectional queries use `$or` on both participant fields (e.g., `{"$or": [{"fromUser": a, "toUser": b}, {"fromUser": b, "toUser": a}]}`).
- Recommendation cleanup uses `$pull` with `update_many({}, ...)` — a full-collection scan on every match event.
- Chat retrieval is O(N) per conversation list: one `find_one` per matched partner (no aggregation).

## 4. Gaps / TODOs

- **Only one index declared (`users.email`, unique+sparse).** Queries on `users.id`, `likes.fromUser/toUser`, `matches.user1_id/user2_id`, `notifications.toUser`, `recommendations.userId`, and `chat_messages` all still do full collection scans.
- **`matchedWith` legacy type drift.** Three separate services contain `_normalize_matched_with` to handle old `int`/`null` values — indicates a past schema migration was never enforced.
- **`matches` missing `compatibilityScore`.** The `ConfirmedMatch` model has it; `likeService` never writes it.
- **`clusters` collection** is written but never read for actual matching — `recommendationService` iterates all users directly.
- **No TTL indexes** on `notifications` or `likes`.

## 5. Notable Decisions

- **Integer IDs over ObjectId.** All inter-collection references use custom integer `id` fields, making cross-collection joins by integer straightforward but requiring manual uniqueness management.
- **Async-only access.** Every DB call uses `await`; no synchronous fallbacks exist.
- **Like records are ephemeral.** Mutual likes are immediately deleted after a match forms, so `likes` only holds pending one-way likes.
- **Gender-gated matching is enforced at service layer**, not at the DB level — two places (likeService, recommendationService) each enforce it independently.
- **`users.email` unique sparse index** means duplicate-email attempts raise a Motor `DuplicateKeyError` at the DB layer, in addition to the application-level 409 check.
- **`migrate_add_auth_fields.py`** exists at the backend root — a one-off migration script that also creates the `users.email` index, evidencing a past auth schema migration that added the `hashed_password` field.
- **Atomic ID generation (P1.1, 2026-06-02).** The previous max-plus-one `get_next_id()` race condition was resolved. `authRoutes.py` now uses `find_one_and_update` with `$inc` on the `counters` collection (`upsert=True`, `ReturnDocument.AFTER`). On first startup, `main.py` lifespan seeds the counter from the current max user ID via `$setOnInsert` so all existing IDs are preserved.
