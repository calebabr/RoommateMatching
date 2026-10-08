# Performance & Index Review (P3D.7)

Date: 2026-09-03 · Reviewed against `roommatch` @ localhost · 501 users
Owner: Database Agent · Indexes live in `backend/migrate_indexes.py`

---

## 0. What this review can and cannot tell you

**Read this before quoting any number below.**

`explain()` was run against the local database, which holds 501 users but **0 likes,
0 chat messages, 0 blocks, 1 match and 4 notifications**. That means:

* **Plan shape is trustworthy.** Whether a query uses an index or falls back to a
  `COLLSCAN` is a property of the query and the index set, not of row count. Every
  "index used" conclusion below is real.
* **Magnitudes are not.** `totalDocsExamined` of 0 on an empty collection proves
  nothing about behaviour at scale. No latency figure here was measured against a
  realistic corpus.

Where this document projects to 5000 users it is **extrapolation from a measured
per-operation cost**, and it says so and shows the arithmetic. It is not a
measurement. A clean `explain()` against 501 users is not evidence of health at
5000, in the same way a clean dry run against already-migrated data was not
evidence that the P3D.1 migration worked.

**The one benchmark that is real:** `matchScore.compatibilityScore()` timed over
400 real user documents — 190 gender-compatible pairs in 0.5 ms, **2.8 µs per
call**. The complexity analysis in §3 is built on that measured constant.

---

## 1. Index coverage — every hot query

Verified by `explain()` after the additions in §2. `EXPRESS_IXSCAN` is MongoDB 8's
fast path for a single-equality indexed lookup.

| Collection | Query | Plan | Index |
|---|---|---|---|
| users | `{id: X}` — ubiquitous | EXPRESS_IXSCAN | `users_id_unique` |
| users | `{email: X}` — login | EXPRESS_IXSCAN | `email_1` (see §5.1) |
| users | `{username: X}` — register dup-check | IXSCAN | `users_username` ✅ new |
| users | `{refresh_token_hash: X}` — `POST /auth/refresh` | IXSCAN | `users_refresh_token_hash` ✅ new |
| users | `{id: {$in: [...]}}` — discover candidates | IXSCAN | `users_id_unique` |
| users | `{deletedAt: {$exists: false}}` — `GET /users/all` | **COLLSCAN** | — (inherent, §5.2) |
| users | active-pool `$and` of `$ne` — nightly job | **COLLSCAN** | — (inherent, §5.2) |
| likes | `{toUser: X}` | IXSCAN | `likes_to_user` |
| likes | `{fromUser: X, toUser: Y}` | IXSCAN | `likes_from_to_unique` |
| matches | `$or` on `user1_id`/`user2_id` | IXSCAN (OR) | `matches_user1` + `matches_user2` |
| notifications | `{toUser: X}` sort `createdAt` desc | IXSCAN, no SORT stage | `notifications_to_user_created` ✅ new |
| notifications | `{toUser: X, read: false}` count | IXSCAN | `notifications_to_user_read` |
| chat_messages | `$or` pair, sort `createdAt` | IXSCAN | `chat_conversation` |
| recommendations | `{userId: X}` — discover read | EXPRESS_IXSCAN | `recommendations_user_unique` |
| groups | `{memberIds: X}` | IXSCAN (multikey) | `groups_memberIds` |
| group_invites | `{toUserId: X, status: "pending"}` | IXSCAN | `group_invites_toUser_status` |
| swipes | `{user_id: X}` | IXSCAN | `swipes_user_id` |
| blocks | `$or` on `blockerId`/`blockedId` — every discover | IXSCAN | `blocks_blocker` / `blocks_blocked` ✅ new |
| chat_read_status | `{user_id: X, partner_id: Y}` | IXSCAN | `chat_read_status_pair` ✅ new |
| outcomes | `{userId: X}` | IXSCAN | `outcomes_userId` |

**Every hot query is now index-served except the two inherent full scans in §5.2.**

---

## 2. Indexes added by this review

Four hot paths were doing full collection scans. All are now covered.

| Index | Fixes |
|---|---|
| `users_refresh_token_hash` (sparse) | **`POST /auth/refresh` was a COLLSCAN of `users`** — the hottest unindexed query in the app, hit by every active session on every token rotation. Sparse because the field only exists while a refresh token is outstanding. |
| `users_username` | Register duplicate-check was a COLLSCAN. Left **non-unique deliberately** — see §5.3. |
| `blocks_blocker`, `blocks_blocked`, `blocks_pair` | **The `blocks` collection had no indexes at all**, yet `get_blocked_ids()` runs an `$or` over both fields on *every discover request*. |
| `chat_read_status_pair` | Read once per conversation open, and once per partner inside the unread-count loop. |
| `notifications_to_user_created` (`toUser` ↑, `createdAt` ↓) | Regression I introduced in P3D.3 — see §2.1. |
| `reports_status_created`, `conversation_reports_status_created` | Admin queues; low traffic, cheap to cover. |

### 2.1 A regression the TTL index caused

Worth recording because it was self-inflicted. Before P3D.3, the notification list
query used `notifications_to_user` plus an in-memory sort. After I added
`notifications_ttl` on `createdAt`, the planner switched to **the TTL index**,
walking notifications in global `createdAt` order and filtering by `toUser`.

That looks fine on an empty collection and is pathological at scale: to fill one
user's page of 50 it walks *everyone's* notifications newest-first. With 500k
notifications and a user holding 50 of them, that is a scan of a large fraction of
the collection to return one page.

`notifications_to_user_created` serves both the equality and the sort, and the
planner now picks it. **Lesson: adding a TTL index can silently change plan
selection for unrelated queries on the same collection.** The same check was run
against `likes_ttl` and `recommendations_ttl` — neither changed any plan, because
no query on those collections sorts by the TTL field.

`notifications_to_user` is now a redundant prefix of the new compound index. It is
left in place rather than dropped in this pass; drop it once the compound is
confirmed in production.

---

## 3. Matching complexity at 5000 users

Measured constant: **2.8 µs per `compatibilityScore()`**, **0.48 ms per
`recommendations` upsert round-trip** (localhost; Atlas will be 2–5 ms).
The gender gate halves the candidate set, so a pass over `n` users costs ≈ `n/2` scores.

| Operation | Complexity | n=501 (today) | n=5000 (projected) |
|---|---|---|---|
| `recompute_for_user` (one user) | O(n) | 0.7 ms | **6.9 ms** |
| `recompute_all` / `recompute_all_active` | O(n²) + n writes | 0.3 s | **≈35 s CPU + 2.4 s writes local / 10–25 s on Atlas** |
| `on_new_user` (**per registration**) | O(n²) + n writes | 0.3 s | **same ≈35–60 s** |

### 3.1 The finding that matters: every registration triggers a full O(n²) recompute

`on_new_user` recomputes the target **and then loops over every other user calling
`recompute_for_user` again** — each of which itself loops all candidates. It is
`recompute_all` in all but name. `create_user` and `recompute_for_user_id` both
route into it.

At 501 users this is invisible (0.3 s). At 5000 users **one signup costs ~35 s of
CPU plus 5000 sequential awaited writes.** It is a FastAPI `BackgroundTask`, so it
does not block the HTTP response — but it runs **in the same process and event
loop**, and the inner scoring loop has no `await` in it. The loop yields only at
each `update_one`, so the event loop is blocked in ~7 ms slices, 5000 times, per
signup. Concurrent signups queue and compound.

This matters most exactly when it hurts most: a roommate app's traffic is a spike
at the start of a semester, which is a signup rush.

**Recommendation (Backend-owned, `recommendationService.py`):** a new user cannot
change any existing user's top-10 unless they *beat* that user's current 10th
entry. So the O(n²) fan-out is unnecessary:

1. Compute the new user's own list — O(n), ~7 ms.
2. Score the new user against each existing user once — O(n), ~7 ms.
3. For each, compare to their stored 10th score and only rewrite the ones that
   actually change — typically a small fraction of `n`, and batchable via
   `bulk_write` instead of `n` sequential round-trips.

That turns ~35 s into well under a second, and is behaviour-preserving: it produces
the same lists, because entries that cannot enter the top 10 cannot alter it.

### 3.2 The nightly job is fine; the write pattern is not

`recompute_all_active` at 04:00 UTC costs ~35 s CPU at 5000 users. For an off-peak
scheduled job that is acceptable. The `n` sequential `await update_one` calls are
the weaker half — at Atlas latency that is 10–25 s of pure round-trip time that
`bulk_write` would collapse into a handful of batches. Worth doing, not urgent.

**Scaling ceiling:** O(n²) means 10k users costs ~140 s and 20k users ~9 minutes.
The nightly job stays viable to roughly 10–15k users. Beyond that the scoring pass
needs blocking (only score plausible candidates) rather than an all-pairs sweep.
Notably, that is precisely what the deleted `clusterService` was reaching for — the
idea was sound, the implementation was simply never wired up. If the app approaches
that scale, revisit candidate blocking, keyed on the gender gate plus the P3FT.10
housing hard filters, both of which already partition the space cheaply.

---

## 4. The four questions

### 4.1 Is the Python-side filtering in `top-matches` fine at 5000 users? **Yes — but for a reason that exposes a worse problem.**

The Python work is **not** O(n). `recompute_for_user` stores only the top
`n=10` matches, so `recommendations.matches` holds at most 10 entries. Every
downstream loop — exclusions, housing compatibility, budget overlap, the move-in
multiplier, and all eight P3FT.16 filter predicates — iterates **at most 10
candidates**, and the `$in` fetches at most 10 documents on `users_id_unique`.

The request path is therefore **O(1) with respect to total user count.** It costs
the same at 5,000,000 users as at 501. Moving those predicates into MongoDB would
gain nothing and would cost more: it would replace ~10 in-memory comparisons with
additional index lookups and a more complex query plan.

**Which predicates *could* move, specifically:** only the ones that compare a
candidate against a constant — `major`, `gradYearMin`/`gradYearMax`, `tags`,
`religion`, `minScore`, and the `is_deactivated`/`is_paused`/`roommateFound`
exclusions. The rest **cannot become index lookups at all**, because they compare
two users' fields *against each other*: `housing_compatible` (viewer's
`housingType` vs candidate's), `budget_compatible` (range *overlap* between two
users), and `move_in_penalty` (season/year agreement). These are relational
predicates; an index can only answer them if you build a per-viewer query at
runtime from the viewer's own values, which is strictly more work than the ten
comparisons it would replace.

**So: leave the filtering in Python.** But the reason it is cheap is the real
problem:

> **⚠ Filter starvation.** The P3FT.16 spec required filters to be applied
> "AFTER the existing exclusions and BEFORE the limit so the page is not starved."
> The limit is **already applied at recompute time** (`scores[:10]`). Filters run
> against a pre-computed top-10 that was ranked with no knowledge of them.
>
> A user who filters by major gets `matches: [], filteredOut: 10` whenever none of
> their top 10 happen to match — even if 200 compatible users with that major sit
> just below the cut. The discover feed can never show anyone outside a fixed 10,
> no matter how the user filters, and the UI then invites them to "widen" filters
> that were never the binding constraint.
>
> This is a correctness bug, not a performance one, and it gets **worse** as the
> user base grows: at 5000 users a fixed top-10 is a far smaller slice of the
> viable pool than at 501. Fixes, cheapest first: (a) store more candidates
> (`n=100`) so filters have room to work — costs ~10× the `recommendations`
> document size, still trivial at ~10 entries/user today; (b) apply filters during
> scoring on a filtered recompute. Backend-owned; flagging, not implementing.

### 4.2 Is a top-matches cache still the right answer? **No. It already exists.**

`recommendations` **is** the cache. It is a materialized, precomputed top-10 per
user, read by a single `EXPRESS_IXSCAN` `find_one` returning one small document —
1 document examined, 1 returned. That is already the cheapest read this codebase
has, and there is no measured read-side problem to solve.

Adding an in-process or Redis cache in front of it would:

* cache a query that is already a single indexed primary-key lookup;
* add an invalidation surface that the nightly job, the TTL, `on_user_matched`'s
  `$pull`, and the per-save recompute would all need to participate in;
* risk serving a *stale* feed containing users who have since paused, blocked the
  viewer, or found a roommate — the exclusions that the request path applies
  *after* the cached read.

**Recommendation: do not add caching.** `nightly_recompute` plus the P3D.6 TTL plus
the existing `recommendations` document already deliver everything the task's
"caching" line was reaching for. The genuine cost is on the **write** side (§3.1),
and a read cache does not touch it. If the task entry stays open, it should be
reframed from "cache top-matches" to "stop recomputing the world on every signup."

### 4.3 Do the TTLs still hold now that a recompute job exists? **Yes, with one caveat.**

* **`likes_ttl` (180 d)** — unaffected. No interaction with recompute.
* **`notifications_ttl` (90 d)** — retention unaffected, but it caused the plan
  regression in §2.1, now fixed.
* **`recommendations_ttl` (7 d)** — now enabled, and the interaction is *better*
  than expected. An active user's document is rewritten nightly, so `computedAt`
  refreshes daily and the doc never approaches 7 days. In practice the TTL only
  reaps documents for users who have **left the active pool** — exactly the
  orphaned rows worth collecting. The 7-day window is generous against a 24-hour
  rebuild cycle.

> **⚠ Caveat — the unpause gap.** `recompute_all_active` covers only *active* users.
> A paused, deactivated, or roommate-found user's recommendations expire after 7
> days. When they return, `get_top_matches` finds no document and the route returns
> **404 "No recommendations yet"** until the next 04:00 run — an empty discover feed
> for up to 24 hours after unpausing. Cheap fix (Backend): call
> `recompute_for_user_id` on unpause/undo, which is a single O(n) ~7 ms pass.

### 4.4 Extrapolation honesty

Stated up front in §0 and inline at every projected figure. The measured basis is
2.8 µs/score over 400 real user documents and 0.48 ms/upsert locally; everything at
n=5000 is arithmetic on those two constants, not observation. The projections
exclude Atlas network latency for the CPU figures and flag it separately for writes.

---

## 5. Deploy notes

### 5.1 ⚠ Deploy blocker: index-name conflict crashes app startup

**Reproduced, not theorised.** `main.py`'s `lifespan` hook (line 108) runs:

```python
await users_collection.create_index("email", unique=True, sparse=True)
```

which MongoDB auto-names `email_1`. `migrate_indexes.py` creates the same key
pattern under the name `users_email_unique`. MongoDB rejects a second index with
identical keys and a different name:

```
code=85 IndexOptionsConflict: Index already exists with a different name: users_email_unique
```

**Order matters, and only one order works:**

* App first, then migration (how local happened to go) → the migration's `_create`
  catches the conflict and prints `[skip]`. Fine.
* **Migration first, then app** → the `lifespan` call raises. It is **not** inside a
  `try/except` (unlike the cleanup blocks below it), so **startup fails and the app
  does not come up.**

The second order is exactly the P3D.10 plan: migrate fresh Atlas, then deploy.

**Fix (Backend-owned, one line):** delete the `create_index` call from `lifespan` —
`migrate_indexes.py` is the single source of truth for indexes — or wrap it in the
same non-fatal `try/except` as its neighbours. **Do this before P3D.10.** Local
confirms it: `users` has `email_1` and *not* `users_email_unique`.

### 5.2 The two remaining COLLSCANs are inherent

`GET /users/all` (`{deletedAt: {$exists: false}}`) and `get_all_active_users`
(a conjunction of `$ne` negations) both **return every matching document**. No index
helps a query whose result set is the whole collection — MongoDB correctly prefers a
sequential scan. Adding an index here would be write overhead for nothing, the same
conclusion reached for `users_housingType_gender` and `users_roommateFound`.

The real concern is **payload, not plan**: `GET /users/all` returns every user
document, unpaginated, over the wire. At 501 users that is ~0.4 MB; at 5000 it is
~4 MB per call. Pagination is the fix, and it is Backend-owned.

### 5.3 Two indexes deliberately left non-unique

`users_username`, `blocks_pair`, and `chat_read_status_pair` all *should* be unique
by their data model, and are not.

Reason: `_create()` skips `IndexOptionsConflict`/`IndexKeySpecsConflict`, but a
unique build that fails because of **pre-existing duplicate data** raises a
different error and would **abort the whole migration**. Local has no duplicate
usernames, but local is not production.

**To tighten:** run a `$group`/`$match` duplicate check on production, resolve any
duplicates, then rebuild these three as `unique=True`. Until then a non-unique index
delivers the full read benefit with no deploy risk.

### 5.4 Current index footprint

52 indexes across all collections; `users` carries 5 (`_id_`, `email_1`,
`users_id_unique`, `users_username`, `users_refresh_token_hash`) for 0.18 MB against
0.4 MB of data at 501 users. Write amplification on the hottest collection stays
modest, consistent with the standing decision not to index `housingType`,
`roommateFound`, `is_paused`, or `is_deactivated`.

---

## 6. Summary of recommendations

| # | Recommendation | Owner | Priority |
|---|---|---|---|
| 1 | Remove/guard the `create_index` in `main.py` `lifespan` — **blocks P3D.10** | Backend | **Blocker** |
| 2 | Make `on_new_user` incremental (O(n), `bulk_write`) instead of O(n²) per signup | Backend | **High** |
| 3 | Fix filter starvation — store more than 10 candidates, or filter during scoring | Backend | **High** |
| 4 | Recompute on unpause/undo to close the 24 h empty-feed gap | Backend | Medium |
| 5 | Paginate `GET /users/all` | Backend | Medium |
| 6 | Batch the nightly job's `n` sequential upserts into `bulk_write` | Backend | Medium |
| 7 | Tighten the three non-unique indexes after a production dupe-check | DB | Low |
| 8 | Drop the now-redundant `notifications_to_user` once the compound is confirmed | DB | Low |
| 9 | Revisit candidate blocking if the user base approaches 10–15k | Backend + DB | Future |

Items 1–6 are all in files owned by the Backend Agent; none were modified by this
review. Items 7–8 are DB-owned and deferred deliberately, not forgotten.
