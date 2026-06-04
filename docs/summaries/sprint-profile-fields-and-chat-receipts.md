# Sprint Summary — Profile Fields & Chat Read Receipts

_Completed: 2026-06-04_

---

## Overview

Four independent features shipped in this sprint: iMessage-style chat read receipts (the largest change), plus three display-only profile fields — religion tag, major, and graduation year/season.

---

## Task 1: Chat Read Receipts (iMessage-style)

### Backend (`backend/app/`)

**New MongoDB collection**

`database.py` — added `chat_read_status_collection = db["chat_read_status"]`. Documents have the shape `{user_id, partner_id, last_read_at}` where `last_read_at` is a proper BSON `datetime` object (not an ISO string), which enables `$gt` comparison against `chat_messages.createdAt` in the unread-count query.

**New and updated endpoints in `userRoutes.py`**

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `POST /api/chat/{partner_id}/mark-read` | 60/min | Upserts `{user_id, partner_id, last_read_at=datetime.now(timezone.utc)}` into `chat_read_status_collection` |
| `GET /api/users/{user_id}/unread-chats` | 60/min | Ownership-gated; returns `{unread_count: int, unread_partner_ids: [int]}` by comparing each partner's last message timestamp against the caller's `last_read_at` for that conversation |
| `GET /api/users/{user_id}/chat/{partner_id}` | existing | Response shape changed from a bare list to `{messages: [...], partner_last_read_at: str|null}` — the `partner_last_read_at` field is the ISO timestamp of the last time the partner marked this conversation read |

**Bug fix**: Added `timezone` to the `datetime` import in `userRoutes.py` so that `datetime.now(timezone.utc)` produces a timezone-aware BSON datetime. Without this fix `$gt` comparisons against the `createdAt` timestamps in `chat_messages` would silently return wrong results.

### Frontend (`frontendv2/src/`)

**`services/api.js`**

Two new functions:

| Function | Endpoint | Purpose |
|----------|----------|---------|
| `markChatRead(userId, partnerId)` | `POST /chat/{partnerId}/mark-read` | Called on conversation open and by poll timer |
| `getUnreadChats(userId)` | `GET /users/{userId}/unread-chats` | Used by App.jsx badge and ChatListPage indicator |

`getChatMessages` updated to destructure `{messages, partner_last_read_at}` from the response instead of treating the response as a bare array.

**`App.jsx`** — unread chat badge on the Chat sidebar nav icon. Polls `getUnreadChats` every 10 seconds. Shows a red numeric badge when `unread_count > 0`.

**`ChatListPage.jsx`** — conversations with unread messages show a filled blue dot and the partner username is rendered in bold. Unread state is derived from the `unread_partner_ids` list returned by `getUnreadChats`.

**`ChatPage.jsx`** — four UX additions:
- **Mark read on open and polling**: calls `markChatRead` immediately on mount and then every 10 seconds while the conversation is open.
- **"New messages" divider**: a horizontal rule with "New messages" label inserted in the message list at the point where unread messages begin (first message sent after the current user's `last_read_at`).
- **"Seen [time]" receipt**: rendered below the current user's last message when `partner_last_read_at` indicates the partner has read past that message.
- **Relative timestamps**: message timestamps display as "just now", "Xm ago", "Xh ago", or "Xd ago" rather than raw ISO strings.

### Tests

`backend/tests/test_chat_read_receipts.py` — 9 tests:

| Test | Assertion |
|------|-----------|
| `test_mark_read_requires_auth` | 401 without token |
| `test_mark_read_upserts` | 200 on first call; second call also 200 (upsert, not insert-only) |
| `test_unread_count_initial` | Count reflects messages sent before any mark-read |
| `test_unread_count_drops_after_mark_read` | Count decreases to 0 after marking read |
| `test_unread_count_wrong_user_403` | 403 when requesting another user's unread count |
| `test_partner_last_read_at_in_response` | `GET /chat/{partner_id}` returns `partner_last_read_at` key |
| `test_partner_last_read_at_null_before_read` | `partner_last_read_at` is null if partner has never marked read |
| `test_partner_last_read_at_updates` | `partner_last_read_at` reflects most recent mark-read time |
| `test_mark_read_wrong_user_403` | 403 when marking read for another user |

---

## Task 2: Religion Tag

### Backend

`RegisterRequest` and `UserCreate` in `models.py` accept an optional `religionTag: Optional[str]` field. The field is stored conditionally on the user document (only if provided). It is updatable via `PUT /api/users/{id}`.

The field is **display-only** and does not affect compatibility scoring in `matchScore.py`.

### Frontend

**`SignupPage.jsx` (Step 2)** — a single-select pill section labeled "Religion" was added. Exactly one option can be selected (clicking the selected pill deselects it). Available options are a predefined list of common religion labels plus "Prefer not to say". The selected value is included in the signup API payload as `religionTag`.

**`ProfilePage.jsx`** — in edit mode, the same single-select pill UI is shown so users can update or clear their religion tag. In display mode, if `religionTag` is set it is shown as a read-only pill under the Lifestyle Tags section.

**`UserDetailPage.jsx`** — `religionTag` is displayed as an informational pill on the public profile view.

---

## Task 3: Major Field

### Backend

`RegisterRequest` and `UserCreate` accept an optional `major: Optional[str]` field. Stored conditionally; updatable via `PUT /api/users/{id}`. Display-only; does not affect scoring.

### Frontend

**`SignupPage.jsx` (Step 0)** — a `<select>` dropdown with a curated list of majors common at Auburn University. When "Other" is selected, a free-text `<input>` appears for the user to type their major. The value (either from the dropdown or the text input) is sent as `major` in the signup payload.

**`ProfilePage.jsx`** — same dropdown + "Other" free-text pattern in edit mode. Display mode shows the major as plain text under the basic info section.

**`UserDetailPage.jsx`** — `major` is displayed as an informational line on the public profile view.

---

## Task 4: Graduation Year & Season

### Backend

`RegisterRequest` and `UserCreate` accept two optional fields:
- `graduationSeason: Optional[str]` — one of `"Spring"`, `"Summer"`, `"Fall"`, `"Winter"`
- `graduationYear: Optional[int]` — four-digit year

Both are stored conditionally; both are updatable via `PUT /api/users/{id}`. Display-only; do not affect scoring.

### Frontend

**`SignupPage.jsx` (Step 0)** — two adjacent dropdowns: a season `<select>` (`Spring / Summer / Fall / Winter`) and a year `<select>` (current calendar year through current year + 6). Both optional; neither blocks form progression if left blank.

**`ProfilePage.jsx`** — same dual-dropdown UI in edit mode. Display mode shows the full graduation string (e.g. "Spring 2027") under the basic info section when both fields are set.

**`UserDetailPage.jsx`** — graduation semester is displayed as an informational line on the public profile view when set.

---

## Files Changed

### New files
- `backend/tests/test_chat_read_receipts.py`

### Modified files
- `backend/app/database.py` — `chat_read_status_collection`
- `backend/app/models.py` — `religionTag`, `major`, `graduationSeason`, `graduationYear` on `RegisterRequest` and `UserCreate`
- `backend/app/routers/userRoutes.py` — `mark-read` endpoint, `unread-chats` endpoint, updated `GET /chat/{partner_id}` response, `timezone` import fix
- `frontendv2/src/services/api.js` — `markChatRead`, `getUnreadChats`, updated `getChatMessages`
- `frontendv2/src/App.jsx` — unread chat badge on nav icon
- `frontendv2/src/pages/ChatListPage.jsx` — unread dot + bold username
- `frontendv2/src/pages/ChatPage.jsx` — mark-read on open/poll, "New messages" divider, "Seen" receipt, relative timestamps
- `frontendv2/src/pages/SignupPage.jsx` — religion pills (Step 2), major dropdown + Other free-text (Step 0), graduation dropdowns (Step 0)
- `frontendv2/src/pages/ProfilePage.jsx` — religion, major, graduation in edit + display mode
- `frontendv2/src/pages/UserDetailPage.jsx` — religion, major, graduation display

---

## Known Limitations / Follow-on Tasks

- **Read receipts are polling-based** (10s interval) — the same limitation as the rest of the chat system. Resolving this requires WebSocket/SSE (tracked as P3F.1).
- **Religion, major, and graduation fields are not indexed** — fine at MVP scale; consider sparse indexes if these fields are ever used for filtering/search.
- **No scoring impact** — all three profile fields are display-only. Future work could explore soft preference filtering (e.g. "prefer same graduation year") if user feedback warrants it.
