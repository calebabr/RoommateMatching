# MongoDB Injection Audit — RoomMatch Backend

**Date:** 2026-05-29
**Auditor:** Security Review (automated)
**Scope:** All Motor query calls in `backend/app/` — routers, services, and auth dependencies

---

## Executive Summary

The RoomMatch backend is in **good overall shape** with respect to MongoDB injection. No `$where`, `$function`, `$accumulator`, mapReduce, regex-on-user-input, or string-concatenated query objects were found anywhere in the codebase. Across approximately 60 individual query operations reviewed, the large majority are **SAFE** because all filter values are either hardcoded literals or derived from Pydantic-validated `int`, `str`, or structured `Preference` model fields that reject operator-injection payloads at deserialization time. Two findings require attention before production: (1) `userProfileService.update_profile` passes an unfiltered Pydantic `model_dump()` dict directly into a `$set` payload, allowing a caller to overwrite security-sensitive fields such as `hashed_password`, `matchCount`, and `id`; (2) `authRoutes.RegisterRequest` declares all preference fields as `Optional[dict]`, not the stricter `Preference` model used elsewhere, meaning that on the registration path a crafted preference value is stored verbatim in the database and never validated against the `Preference` schema. One additional note covers the `limit` query parameter in chat that accepts an unbounded user-supplied integer.

---

## Methodology

Each file was read in full. For every Motor call (`find_one`, `find`, `insert_one`, `update_one`, `update_many`, `delete_one`, `delete_many`, `count_documents`, `aggregate`, `create_index`) the following were checked:

- **A. String concatenation / f-string query building** — any dynamic construction of a query dict from raw string input.
- **B. JavaScript evaluation operators** — `$where`, `$function`, `$accumulator`, `mapReduce`.
- **C. Regex on user input** — `$regex` with an unescaped user-supplied value.
- **D. Operator injection via Pydantic models** — whether a field's declared Python type allows a dict `{"$ne": null}` to pass through.
- **E. Dynamic field construction** — `{user_supplied_key: value}` patterns in query or `$set` dicts.
- **F. $set payload scope** — whether a `$set` built from user input can touch fields that should be immutable (id, hashed_password, matchCount, matched, matchedWith).

---

## Query Inventory

### `authRoutes.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 1 | `find_one(sort=[("id", -1)])` (L42) | none — sort only | SAFE | No user input in filter |
| 2 | `find_one({"email": body.email.lower()})` (L49) | `RegisterRequest.email` — Pydantic `str` | SAFE | `str` field rejects dict injection |
| 3 | `insert_one(user_doc)` (L82) | `RegisterRequest` fields | **FINDING-1** | `Optional[dict]` preference fields stored verbatim — see FINDING-1 |
| 4 | `find_one({"email": body.email.lower()})` (L93) | `LoginRequest.email` — Pydantic `str` | SAFE | `str` rejects dict |
| 5 | `find_one({"id": current_user["id"]})` (L125) | JWT-derived `int` from `get_current_user` | SAFE | Value comes from verified token, is cast to `int` |
| 6 | `update_one({"id": current_user["id"]}, {"$set": {"hashed_password": ...}})` (L132) | JWT `int` filter; `$set` value is a bcrypt hash string — not user-supplied | SAFE | `$set` payload is fully server-constructed |

---

### `userRoutes.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 7 | `collection.find({})` (L39) | none | SAFE | Empty filter, no user input |
| 8 | `collection.update_one({"id": user_id}, {"$set": {"photoUrl": photo_url}})` (L311) | `user_id` — path `int`; `photo_url` — Cloudinary-returned string | SAFE | Both values are server-controlled; user cannot inject field names or operators |

All other queries in `userRoutes.py` are delegated to service classes audited below.

---

### `matchingRoutes.py`

No direct MongoDB queries. All database access is delegated to `UserProfileService` and `RecommendationService`. The `/uploadUsers` endpoint (L37) feeds raw JSON file contents into `userProfileService.create_user` — see NOTE-2.

---

### `userProfileService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 9 | `find_one(sort=[("id", -1)])` (L18) | none | SAFE | No user input |
| 10 | `find_one({"username": user_data["username"]})` (L37) | `user_data["username"]` — passes through `UserCreate.username` (`str`) on normal path | SAFE | `str` rejects dict |
| 11 | `find_one({"email": user_data["email"]})` (L42) | `user_data["email"]` — `Optional[str]` | SAFE | `str` field rejects dict; guarded by `if user_data.get("email")` |
| 12 | `insert_one(user_data)` (L58) | full `user_data` dict | NOTE-2 | On `/uploadUsers` path, `user_data` comes from raw JSON file with no Pydantic validation — see NOTE-2 |
| 13 | `find_one({"id": user_id})` (L75) | route path `int` | SAFE | Python path param typed as `int` |
| 14 | `find_one({"id": user_id})` (L96) | route path `int` | SAFE | |
| 15 | `find_one_and_update({"id": user_id}, {"$set": preferences}, ...)` (L100) | `user_id` — path `int`; `preferences` — `UserCreate.model_dump(exclude_none=True)` | **FINDING-2** | `$set` payload is the full Pydantic dump including `id`, `hashed_password` (if submitted), `matchedWith`, etc. — see FINDING-2 |
| 16 | `find_one({"id": user_id})` (L124) | path `int` | SAFE | |
| 17 | `find_one({"id": partner_id})` (L140) | `partner_id` — comes from `user.matchedWith` list stored in DB (server-controlled) | SAFE | |
| 18 | `update_one({"id": partner_id}, {"$set": {...}})` (L146) | filter: DB-sourced `int`; `$set` dict keys are hardcoded literals | SAFE | |
| 19 | `matches_collection.delete_many({"$or": [...]})` (L154) | `user_id`, `partner_id` — both `int` | SAFE | |
| 20 | `delete_one({"id": user_id})` (L162) | path `int` | SAFE | |
| 21 | `likes_collection.delete_many({"$or": [...]})` (L165) | both `int` | SAFE | |
| 22 | `recommendations_collection.update_many({}, {"$pull": {"matches": {"user_id": user_id}}})` (L168) | `int` | SAFE | |
| 23 | `recommendations_collection.delete_one({"userId": user_id})` (L172) | `int` | SAFE | |
| 24 | `collection.find({"$or": [{"matchCount": ...}, {"matchCount": ...}]})` (L182) | hardcoded literals only | SAFE | |
| 25 | `find_one_and_update({"id": user_id}, {"$set": {"matched": True, "matchedWith": matched_with}}, ...)` (L207) | both `int` | SAFE | |
| 26 | `find_one_and_update({"id": user_id}, {"$set": {"matched": False, "matchedWith": None}}, ...)` (L231) | path `int` | SAFE | |

---

### `likeService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 27 | `users.find_one({"id": from_id})` (L40) | path `int` | SAFE | |
| 28 | `users.find_one({"id": to_id})` (L44) | `LikeRequest.toUser` — Pydantic `int` | SAFE | `int` rejects dict |
| 29 | `likes.find_one({"fromUser": from_id, "toUser": to_id})` (L65) | both `int` | SAFE | |
| 30 | `likes.find_one({"fromUser": to_id, "toUser": from_id})` (L66) | both `int` | SAFE | |
| 31 | `likes.insert_one({...})` (L73) | `from_id`, `to_id` — both `int` | SAFE | |
| 32 | `notifications.insert_one({...})` (L27) | `notif_type` — hardcoded caller string; `from_user`, `to_user` — both `int`; `message` — server-constructed f-string | SAFE | |
| 33 | `users.find_one({"id": from_id})` (L87) | `int` | SAFE | |
| 34 | `users.find_one({"id": to_id})` (L88) | `int` | SAFE | |
| 35 | `users.update_one({"id": from_id}, {"$set": {...}})` (L102) | `int` filter; `$set` keys hardcoded | SAFE | |
| 36 | `users.update_one({"id": to_id}, {"$set": {...}})` (L106) | `int` filter; `$set` keys hardcoded | SAFE | |
| 37 | `matches.insert_one({...})` (L111) | all `int` or `datetime` | SAFE | |
| 38 | `likes.delete_many({"$or": [...]})` (L129) | both `int` | SAFE | |
| 39 | `recommendations.update_one({"userId": from_id}, {"$pull": ...})` (L137) | `int` | SAFE | |
| 40 | `recommendations.update_one({"userId": to_id}, {"$pull": ...})` (L141) | `int` | SAFE | |
| 41 | `recommendations.update_many({}, {"$pull": ...})` (L147/153) | `int` embedded in `$pull` sub-document | SAFE | |
| 42 | `recommendations.delete_one({"userId": from_id/to_id})` (L150/156) | `int` | SAFE | |
| 43 | `likes.find({"toUser": user_id})` (L176) | path `int` | SAFE | |
| 44 | `likes.find_one({"fromUser": user_id, "toUser": sender_id})` (L187) | both `int` (sender_id from DB doc) | SAFE | |
| 45 | `users.find_one({"id": user_id})` (L204) | `int` | SAFE | |
| 46 | `likes.find({"fromUser": user_id})` (L207) | `int` | SAFE | |
| 47 | `matches.find({"$or": [...]})` (L218) | `int` | SAFE | |
| 48 | `users.find_one({"id": user_id})` (L228) | path `int` | SAFE | |
| 49 | `users.update_one({"id": user_id}, {"$set": {...}})` (L240) | `int` filter; `$set` keys hardcoded | SAFE | |
| 50 | `users.find_one({"id": partner_id})` (L245) | path `int` | SAFE | |
| 51 | `users.update_one({"id": partner_id}, {"$set": {...}})` (L251) | `int` filter; `$set` keys hardcoded | SAFE | |
| 52 | `matches.delete_many({"$or": [...]})` (L262) | both `int` | SAFE | |
| 53 | `likes.delete_many({"$or": [...]})` (L269) | both `int` | SAFE | |

---

### `chatService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 54 | `users.find_one({"id": from_id})` (L23) | path `int` | SAFE | |
| 55 | `messages.insert_one(msg)` (L37) | `from_id`, `partner_id` — `int`; `content` — `ChatMessageCreate.content` (`str`) | SAFE | `str` field; stored as data not used in queries |
| 56 | `messages.find({...}).sort(...).limit(limit)` (L44) | `user_id`, `partner_id` — `int`; `limit` — query param `int` | NOTE-3 | `limit` comes from HTTP query string typed `int` — see NOTE-3 |
| 57 | `users.find_one({"id": user_id})` (L60) | path `int` | SAFE | |
| 58 | `messages.find_one({...}, sort=[...])` (L68) | `user_id`, `partner_id` — both `int` from server-controlled matched_with list | SAFE | |

---

### `notificationService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 59 | `notifications.find({"toUser": user_id}).sort(...).limit(50)` (L10) | path `int` | SAFE | limit is hardcoded `50` |
| 60 | `notifications.count_documents({"toUser": user_id, "read": False})` (L23) | `int` + hardcoded bool | SAFE | |
| 61 | `notifications.update_many({"toUser": user_id, "read": False}, {"$set": {"read": True}})` (L30) | `int`; `$set` is fully hardcoded | SAFE | |
| 62 | `notifications.update_one({"_id": ObjectId(notification_id), "toUser": user_id}, ...)` (L39) | `notification_id` — `str` parsed via `ObjectId()`; `user_id` — `int` | SAFE | `ObjectId()` constructor throws `bson.errors.InvalidId` on malformed input; `user_id` scopes the update to the caller's own notification |

---

### `recommendationService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 63 | `recommendations.update_one({"userId": target_user["id"]}, {"$set": {...}}, upsert=True)` (L36) | `target_user["id"]` — server-computed `int` from `toMatchDict()` | SAFE | |
| 64 | `recommendations.find_one({"userId": user_id})` (L43) | path `int` | SAFE | |
| 65 | `recommendations.update_many({}, {"$pull": {"matches": {"user_id": matched_user_id}}})` (L55) | `int` | SAFE | |
| 66 | `recommendations.delete_one({"userId": matched_user_id})` (L59) | `int` | SAFE | |

---

### `clusterService.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 67 | `clusters.update_one({"userId": user_id}, {"$set": {"clusterId": cluster_id}}, upsert=True)` (L91) | both server-computed `int` values | SAFE | |
| 68 | `clusters.find({"clusterId": {"$in": cluster_ids}})` (L107) | `cluster_ids` — a `list[int]` computed by `get_nearby_clusters()` from K-means centroids | SAFE | No user input reaches this list |

---

### `matchingUsers.py`

No MongoDB queries. This service is purely in-memory (NetworkX graph). SAFE — no injection surface.

---

### `auth/dependencies.py`

| # | Query (approx. line) | Input source | Classification | Notes |
|---|---|---|---|---|
| 69 | `users_collection.find_one({"id": int(user_id)})` (L19) | `user_id` — string from JWT `sub` claim, cast to `int` via `int()` | SAFE | `int()` will raise `ValueError` on a non-integer string, returning 401 |
| 70 | `matches_collection.find_one({"$or": [...]})` (L38) | `user_id`, `partner_id` — FastAPI path params typed `int` | SAFE | |

---

## Pydantic Model Analysis

### `Preference` model (`models.py` L9)
```python
class Preference(BaseModel):
    value: float
    isDealBreaker: bool
```
Any attempt to send `{"value": {"$gt": 0}, "isDealBreaker": False}` will fail Pydantic validation because `value` is typed `float`. **SAFE for operator injection.**

### `UserCreate` — preference fields
All nine preference fields (`sleepScoreWD`, etc.) are declared as `Preference` (a nested Pydantic model). Sending `{"sleepScoreWD": {"$ne": null}}` will be rejected with a validation error. **SAFE.**

### `RegisterRequest` in `authRoutes.py` — preference fields (`authRoutes.py` L19-28)
```python
sleepScoreWD: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
# ... (all nine preference fields are Optional[dict])
```
These fields are `Optional[dict]`, **not** `Preference`. Pydantic will accept any dict, including `{"$where": "..."}` or `{"value": {"$gt": 0}, "isDealBreaker": False}`. The values are stored verbatim into MongoDB via `insert_one(user_doc)`. While these stored dicts are never used as MongoDB query filters, they are served back to clients and may cause unexpected application behavior — and represent inconsistent validation versus the `UserCreate` model. See **FINDING-1**.

### `UserCreate` — `id`, `hashed_password`, `password` fields
`UserCreate` includes `password: Optional[str]` (L22) and does **not** include `id` or `hashed_password`. However, `model_dump(exclude_none=True)` is passed directly to `$set` in `update_profile`. If a caller omits `password=None` and the model does not emit it, that field is fine — but other sensitive computed fields like `matched`, `matchCount`, and `matchedWith` **are** included in `UserCreate` if a subclasser or future developer adds them. See **FINDING-2** for the current exploitable path.

### `LikeRequest`, `MatchScoreRequest`, `ChatMessageCreate`
All use `int` or `str` primitive types. **SAFE.**

---

## Findings

### FINDING-1: `RegisterRequest` preference fields use `Optional[dict]` instead of `Preference`

**File:** `backend/app/routers/authRoutes.py`, lines 19-28 and 82  
**Severity:** Low-Medium (data integrity / defense-in-depth)

**Description:**  
The `RegisterRequest` model declares all nine lifestyle preference fields as `Optional[dict]`:
```python
sleepScoreWD: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
```
Pydantic will accept **any** dict for these fields, including malformed data like `{"value": "not-a-float", "isDealBreaker": "yes"}` or even operator-flavored structures. These values are stored directly into MongoDB via `insert_one(user_doc)` without further validation.

**Impact:**
- Malformed preference data stored at registration will cause `matchScore.py` to crash or produce incorrect scores when processing this user.
- Any dict value is accepted — there is no type guarantee that `value` is a float and `isDealBreaker` is a bool. This is inconsistent with the rest of the system, which enforces the strict `Preference` model.
- Not a direct query injection risk (the preference dicts are never used as filter values), but represents a data integrity hole and inconsistent validation boundary.

**Fix:**  
Change all nine preference fields in `RegisterRequest` to use the `Preference` model (import from `app.models`):
```python
from app.models import Preference
# ...
sleepScoreWD: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
```

---

### FINDING-2: `update_profile` passes full `UserCreate.model_dump()` directly into `$set`, allowing overwrite of security-sensitive fields

**File:** `backend/app/services/userProfileService.py`, lines 100-104  
**Triggered from:** `backend/app/routers/userRoutes.py`, line 84  
**Severity:** High

**Description:**  
The profile update endpoint receives a `UserCreate` body, dumps it to a dict with `exclude_none=True`, and passes the entire dict as the `$set` payload:

```python
# userRoutes.py L84
preferences = user.model_dump(exclude_none=True)
result = await userProfileService.update_profile(user_id, preferences)

# userProfileService.py L100-104
result = await self.collection.find_one_and_update(
    {"id": user_id},
    {"$set": preferences},   # <-- full user-controlled dict
    return_document=True
)
```

`UserCreate` includes the following fields that are security-sensitive or system-managed:

| Field | Risk if overwritten |
|---|---|
| `password` | Plaintext password stored in the DB (the service does `user_data.pop("password", None)` in `create_user` but **not** in `update_profile`) |
| `email` | Can be changed to another user's email, bypassing the uniqueness check in `create_user` |
| `gender` | Can be changed post-registration to bypass gender-gated matching |

Additionally, while `matched`, `matchCount`, `matchedWith` are not fields on `UserCreate`, any field included in the model (even `id` if it were added) would be blindly written through. The `password` field is particularly dangerous: `UserCreate.password` is `Optional[str]`; if a user submits `{"password": "plaintext"}` in a PUT request, the plaintext password is stored in the document alongside `hashed_password`, which would be discovered on document inspection.

**Attack scenario:**  
An authenticated user sends:
```json
PUT /api/users/42
{
  "username": "...", "gender": "female",
  "password": "leaked_plaintext",
  ...
}
```
The plaintext password is written to MongoDB at field `password`. An attacker who later dumps the DB (or exploits a read vulnerability) obtains cleartext credentials.

**Fix:**  
Explicitly allowlist the fields that `update_profile` may set, or strip sensitive/immutable fields before passing to `$set`:

```python
# In userProfileService.update_profile, before the update call:
IMMUTABLE = {"id", "hashed_password", "password", "matched", "matchCount", "matchedWith", "createdAt"}
safe_prefs = {k: v for k, v in preferences.items() if k not in IMMUTABLE}
result = await self.collection.find_one_and_update(
    {"id": user_id},
    {"$set": safe_prefs},
    return_document=True
)
```

Alternatively, create a dedicated `UserUpdateRequest` Pydantic model that contains only the fields a user is allowed to change (bio, photoUrl, lifestyleTags, preference scores, gender) and does not include `password`, `email`, `id`, or match state fields.

---

## Notes

### NOTE-1: `limit` query parameter in chat is user-controlled with no upper bound

**File:** `backend/app/routers/userRoutes.py` L182; `backend/app/services/chatService.py` L42  
**Severity:** Low (resource exhaustion / DoS)

The `get_chat_messages` endpoint accepts `limit: int = 100` as a query parameter, which is forwarded verbatim to `.limit(limit)`. A caller can request `?limit=10000000`, causing MongoDB to attempt to return an arbitrarily large cursor in a single response, consuming server memory and potentially timing out.

**Fix:**  
Cap the limit on the server side:
```python
async def get_chat_messages(..., limit: int = 100, ...):
    limit = min(max(limit, 1), 500)  # clamp to [1, 500]
```

---

### NOTE-2: `/uploadUsers` bulk endpoint passes raw JSON file data through `create_user` without Pydantic validation

**File:** `backend/app/routers/matchingRoutes.py`, lines 37-59  
**Severity:** Low-Medium (data integrity; only accessible to authenticated users)

The `/uploadUsers` endpoint reads arbitrary JSON from an uploaded file and iterates `data["users"]`, passing each raw dict directly to `userProfileService.create_user`. There is no Pydantic deserialization step; the dict is inserted into MongoDB as-is (after a username/email uniqueness check). A malicious authenticated user could upload a JSON file containing users with arbitrary fields, operator-flavored values, or missing required fields, corrupting the recommendations dataset.

**Fix:**  
Validate each entry through the `UserCreate` model before calling `create_user`:
```python
from app.models import UserCreate
for raw in data["users"]:
    try:
        validated = UserCreate(**raw).model_dump()
        await userProfileService.create_user(validated)
        created += 1
    except (ValueError, ValidationError):
        skipped += 1
```

---

### NOTE-3: No `$where`, `$function`, `$accumulator`, or `mapReduce` found anywhere

No JavaScript-executing MongoDB operators were found in any file. This is the most critical injection class in MongoDB and the codebase is clean.

---

### NOTE-4: No regex on user input

No query in the codebase uses `$regex` with a user-supplied value. All text lookups use exact equality. No ReDoS risk via MongoDB.

---

### NOTE-5: `Optional[dict]` preference fields in `RegisterRequest` are never used as query filters

Confirmed: the preference dict fields from `RegisterRequest` flow only into `insert_one(user_doc)` as stored data, never into a `find`, `find_one`, or `update` filter clause. Operator injection into a query filter is therefore not possible via this path. The risk is data integrity only (FINDING-1).

---

## Verdict

**Overall risk level: Medium** — no classic MongoDB injection (no `$where`, no regex-on-input, no f-string query building) was found. Two issues require fixes before production:

1. **FINDING-2 (High)** — `update_profile` must strip `password`, `hashed_password`, `id`, and match-state fields from the `$set` payload. This is the most urgent fix; it allows an authenticated user to store a plaintext password in the database document.

2. **FINDING-1 (Low-Medium)** — `RegisterRequest` preference fields should use the `Preference` model instead of `Optional[dict]` to enforce consistent validation at the registration boundary.

NOTE-1 and NOTE-2 are hardening recommendations that reduce DoS and data-integrity risk but do not constitute injection vulnerabilities.
