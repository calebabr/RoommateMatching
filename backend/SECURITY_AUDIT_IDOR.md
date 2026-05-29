# IDOR Security Audit — RoomMatch Backend

**Date:** 2026-05-28
**Auditor:** docs agent
**Scope:** `authRoutes.py`, `userRoutes.py`, `matchingRoutes.py`, `chatRoutes.py`
**Status:** Fully remediated — all IDOR vulnerabilities resolved. Tasks #7–#10, #12 complete.

---

## Executive Summary

### Vulnerability Class

**Insecure Direct Object Reference (IDOR)** — CWE-639, OWASP API Security Top 10: API1:2023.

Most routes in `userRoutes.py` and all routes in `chatRoutes.py` accept a `{user_id}` path parameter and operate on that user's data, but do not verify that the authenticated caller *is* that user. Any valid JWT holder can substitute any other user's ID in the URL and read or mutate their data.

**Concrete attack example (pre-fix):**
```
POST /api/users/42/like        Authorization: Bearer <token for user 99>
```
User 99 can send likes on behalf of user 42, manipulate their match state, read their private chat history, delete their account, or overwrite their profile — all with a valid token for a *different* account.

`chatRoutes.py` is the most severe case: those three endpoints have **no authentication at all**, making them accessible to unauthenticated callers.

### Fix Applied (Tasks #7–#9)

Two new FastAPI dependencies were added to `backend/app/auth/dependencies.py`:

- **`get_current_user_or_403`** — resolves the authenticated user exactly like `get_current_user`, then compares `current_user["id"]` against the `{user_id}` path parameter. Returns `403 Forbidden` if they do not match. Replaces `_: dict = Depends(get_current_user)` on all user-scoped routes in `userRoutes.py` and `chatRoutes.py`.

- **`verify_match_exists`** — queries `matches_collection` for a record pairing `user_id` and `partner_id` (either order). Returns `403 Forbidden` if no match exists. Applied to `POST /users/{user_id}/chat/{partner_id}` and `GET /users/{user_id}/chat/{partner_id}` in `userRoutes.py`, and `GET /chat/{user_id}/messages/{partner_id}` in `chatRoutes.py`.

### Full Remediation of `POST /chat/{user_id}/send` (Task #12)

`verify_match_exists` could not be reused for this route because the receiver is `receiverId` in the **request body**, not a path parameter. Task #12 resolved this with an inline match check directly in the handler: after resolving `get_current_user_or_403`, the handler queries `matches_collection` with a `$or` filter on `(user_id, request.receiverId)` in either order, and raises 403 if no confirmed match exists. No open IDOR items remain.

### Routes Intentionally Left Without IDOR Checks

| Route | Justification |
|---|---|
| `POST /api/auth/register` | Public — no authenticated user exists yet |
| `POST /api/auth/login` | Public — credential verification does not require prior auth |
| `GET /api/auth/me` | Operates on `current_user` from the token — no path parameter, no IDOR surface |
| `GET /api/users/all` | Returns all profiles — no per-user scoping, no IDOR surface |
| `POST /api/users` | Creates a new user record — not scoped to any existing user |
| `POST /api/matchScore` | Computes a score between two users — read-only, no mutation, no private data |
| `POST /api/uploadUsers` | Admin bulk import — no per-user scoping |
| `POST /api/match` | Admin batch operation — no per-user scoping |
| `POST /api/admin/recompute` | Admin operation — no per-user scoping |

> **Note:** `GET /api/users/{user_id}` was originally listed here as intentionally public, but Task #8 applied `get_current_user_or_403` to it — it now requires the caller to be the profile owner. If the recommendation/matching UI needs to display other users' cards, a separate read endpoint with a field projection (excluding sensitive fields) should be introduced.

---

## Route-by-Route Audit Table

### `authRoutes.py` — prefix `/api/auth`

| Route | Method | Auth Required | IDOR Guard | Additional Check | Notes |
|---|---|---|---|---|---|
| `/api/auth/register` | POST | No | N/A | — | Public registration endpoint; rate-limited 3/hour by IP |
| `/api/auth/login` | POST | No | N/A | — | Public login; rate-limited 5/15min by IP |
| `/api/auth/me` | GET | Yes | N/A | — | No path parameter; returns caller's own data from token — no IDOR surface |

### `userRoutes.py` — prefix `/api`

| Route | Method | Auth Required | IDOR Guard | Additional Check | Notes |
|---|---|---|---|---|---|
| `GET /api/users/all` | GET | Yes | N/A | — | Returns all users; no per-user path param — no IDOR surface |
| `POST /api/users` | POST | Yes | N/A | — | Creates new user; not scoped to existing user |
| `GET /api/users/{user_id}` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Now owner-only. Was previously public; see note in Routes Intentionally Left Without IDOR Checks section. |
| `PUT /api/users/{user_id}` | PUT | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — was previously vulnerable to profile overwrite by any authenticated user |
| `DELETE /api/users/{user_id}` | DELETE | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — was previously vulnerable to account deletion by any authenticated user |
| `GET /api/users/{user_id}/top-matches` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — recommendation data now owner-only |
| `POST /api/users/{user_id}/like` | POST | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — likes can only be sent by the acting user |
| `GET /api/users/{user_id}/likes-received` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — like inbox now owner-only |
| `GET /api/users/{user_id}/likes-sent` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — outbound likes now owner-only |
| `GET /api/users/{user_id}/matches` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — match list now owner-only |
| `POST /api/users/{user_id}/unmatch/{partner_id}` | POST | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — unmatch can only be triggered by the acting user |
| `GET /api/users/{user_id}/chat/conversations` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — conversation list now owner-only |
| `POST /api/users/{user_id}/chat/{partner_id}` | POST | Yes | **Yes** (`get_current_user_or_403`) | `verify_match_exists` | Fixed — sender identity verified; match required via `partner_id` path param |
| `GET /api/users/{user_id}/chat/{partner_id}` | GET | Yes | **Yes** (`get_current_user_or_403`) | `verify_match_exists` | Fixed — reader identity verified; match required via `partner_id` path param |
| `GET /api/users/{user_id}/notifications` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — notification inbox now owner-only |
| `GET /api/users/{user_id}/notifications/unread-count` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — notification count now owner-only |
| `POST /api/users/{user_id}/notifications/mark-read` | POST | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — mark-read action now owner-only |
| `POST /api/users/{user_id}/upload-photo` | POST | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — photo upload now restricted to profile owner |
| `POST /api/admin/recompute` | POST | Yes | N/A | — | Global operation; not scoped to a user; uses `get_current_user` (any authenticated user) |

### `matchingRoutes.py` — prefix `/api`

| Route | Method | Auth Required | IDOR Guard | Additional Check | Notes |
|---|---|---|---|---|---|
| `POST /api/matchScore` | POST | Yes | N/A | — | Read-only score computation between two arbitrary users; no private data exposed, no mutation |
| `POST /api/uploadUsers` | POST | Yes | N/A | — | Admin bulk import; no per-user path param |
| `POST /api/match` | POST | Yes | N/A | — | Admin batch match operation; no per-user path param |

### `chatRoutes.py` — prefix `/api`

| Route | Method | Auth Required | IDOR Guard | Additional Check | Notes |
|---|---|---|---|---|---|
| `POST /api/chat/{user_id}/send` | POST | Yes | **Yes** (`get_current_user_or_403`) | Inline match check on `request.receiverId` | Fixed (Task #12) — inline `matches_collection` query raises 403 if sender and receiver have no confirmed match |
| `GET /api/chat/{user_id}/messages/{partner_id}` | GET | Yes | **Yes** (`get_current_user_or_403`) | `verify_match_exists` | Fixed — previously unauthenticated; now requires token + owner identity + confirmed match |
| `GET /api/chat/{user_id}/conversations` | GET | Yes | **Yes** (`get_current_user_or_403`) | — | Fixed — previously unauthenticated; now requires token + owner identity |

---

## Vulnerability Count Summary

### Pre-fix (at time of initial audit)

| Severity | Count | Description |
|---|---|---|
| Critical | 3 | `chatRoutes.py` — no auth, no IDOR guard |
| High | 15 | `userRoutes.py` — authenticated but no IDOR guard on user-scoped routes |
| None | 12 | Routes with no IDOR surface or intentionally public |

### Post-fix (current state)

| Status | Count | Description |
|---|---|---|
| Fixed | 18 | All previously vulnerable routes have `get_current_user_or_403`; chat routes also have match verification (`verify_match_exists` dependency or inline check) |
| No IDOR surface | 12 | Unchanged |

---

## Remediation Status

| Task | Status | Description |
|---|---|---|
| #7 | **Completed** | `get_current_user_or_403` and `verify_match_exists` added to `backend/app/auth/dependencies.py` |
| #8 | **Completed** | `get_current_user_or_403` (and `verify_match_exists` for chat routes) applied to all `userRoutes.py` endpoints |
| #9 | **Completed** | `get_current_user_or_403` and `verify_match_exists` applied to `chatRoutes.py`; `authRoutes.py` and `matchingRoutes.py` confirmed no IDOR surface |
| #10 | **Completed** | Negative pytest tests written confirming 403 on IDOR attempts |
| #12 | **Completed** | Inline match check on `request.receiverId` added to `POST /api/chat/{user_id}/send` — queries `matches_collection` directly in the handler, raises 403 if no confirmed match |
