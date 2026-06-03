# Session Summary: Block System, Report System, and Account Deletion (P2.20–P2.22, P2.24)

**Date:** 2026-06-03
**Project:** RoomMatch
**Focus:** P2.20 account deletion (soft-delete + restore + export + hard-delete), P2.21 report system, P2.22 block system, P2.24 OWASP security audit, password visibility toggle across all password fields

---

## Overview

Five agents completed four backlog tasks in a single session. Three new backend services were introduced: `blockService.py`, `reportService.py`, and `deletionService.py`. All user-facing queries (discover, likes, matches, chat, notifications) were updated to filter soft-deleted and blocked users bidirectionally. A corresponding frontend UI was built: block/report controls on `UserDetailPage`, a Danger Zone and Blocked Users section on `ProfilePage`, and a standalone `RestoreAccountPage` for the 7-day restore window. Password show/hide toggles were added to every password input across the main app and admin app. A full OWASP Top 10 (2021) audit was completed and the report saved at `backend/SECURITY_AUDIT_FINAL.md`. 38 new pytest tests were written across four new files; all pass.

---

## Changes

### `backend/app/services/blockService.py` (new file)

| Method | Behavior |
|--------|---------|
| `block_user(blocker_id, blocked_id)` | Writes to `blocks_collection`; calls `likeService` to auto-unmatch and remove mutual likes |
| `unblock_user(blocker_id, blocked_id)` | Removes block document; does NOT restore matches |
| `is_blocked(user_a, user_b)` | Bidirectional check — returns True if either direction is blocked |
| `get_blocked_ids(user_id)` | Returns set of all user IDs blocked by this user |
| `get_blocked_by_user(user_id)` | Returns full user objects for blocked list display |

---

### `backend/app/services/reportService.py` (new file)

| Method | Behavior |
|--------|---------|
| `create_report(reporter_id, reported_id, reason, description)` | Writes report document; enforces 5-reports-per-day rate check in service layer; auto-blocks reported user from reporter |
| `get_reports(status_filter)` | Returns all reports, optionally filtered by `status` (`open`/`resolved`) |
| `resolve_report(report_id, resolver_id, resolution_note)` | Sets `status="resolved"`, stamps `resolvedAt` and `resolvedBy` |

Report documents include: `reporter_id`, `reported_id`, `reason` (enum), `description` (max 1000 chars), `status`, `createdAt`, `resolvedAt`, `resolvedBy`.

---

### `backend/app/services/deletionService.py` (new file)

| Method | Behavior |
|--------|---------|
| `soft_delete_user(user_id, password)` | Verifies password; sets `deletedAt` timestamp; generates SHA-256 restore token with 7-day expiry; returns plain token |
| `restore_account(token)` | Hashes token, finds matching non-expired document, clears `deletedAt` and restore token fields |
| `export_user_data(user_id)` | Assembles full JSON export: user profile, likes sent/received, matches, chat messages, notifications |
| `hard_delete_user(user_id)` | Full cascade: deletes from all 7 collections + Cloudinary photo removal |
| `cleanup_expired_deletions()` | Finds users where `deletedAt` is older than 7 days and calls `hard_delete_user`; invoked at app startup via lifespan |

---

### `backend/app/database.py`

- Added `blocks_collection` (Motor async collection handle)
- Added `reports_collection` (Motor async collection handle)

---

### `backend/app/models.py`

| Addition | Detail |
|----------|--------|
| `ReportReason` enum | Six values: `harassment`, `inappropriate_content`, `fake_profile`, `spam`, `underage`, `other` |
| `ReportCreate` | `reason: ReportReason`, `description: Optional[str]` (max 1000 chars) |
| `DeleteAccountRequest` | `password: str` |
| `RestoreAccountRequest` | `token: str` |
| `ResolveReportRequest` | `resolution_note: Optional[str]` |

---

### `backend/app/auth/dependencies.py`

- `verify_match_exists` now calls `blockService.is_blocked(user_id, partner_id)` before checking match existence; returns 403 with `"Blocked"` if either party has blocked the other

---

### `backend/app/services/userProfileService.py`

- All active-user queries (discover feed, user listing) now append `{"deletedAt": {"$exists": False}}` to filter soft-deleted accounts out of results

---

### `backend/app/routers/userRoutes.py`

New endpoints added:

| Endpoint | Auth | Behavior |
|----------|------|---------|
| `POST /api/users/{id}/block/{target_id}` | Bearer | Calls `blockService.block_user`; 400 if already blocked; 200 on success |
| `DELETE /api/users/{id}/block/{target_id}` | Bearer | Calls `blockService.unblock_user`; 200 on success |
| `GET /api/users/{id}/blocked` | Bearer | Returns list of blocked user objects |
| `POST /api/users/{id}/report/{reported_id}` | Bearer | Rate-limited 5/day; calls `reportService.create_report` |
| `GET /api/users/{id}/export` | Bearer | Calls `deletionService.export_user_data`; returns JSON |
| `DELETE /api/users/{id}` | Bearer | Soft-delete — requires `DeleteAccountRequest` body with password; returns restore token |
| `GET /api/admin/reports` | Admin | Returns all reports; optional `?status=open|resolved` query param |
| `POST /api/admin/reports/{report_id}/resolve` | Admin | Resolves a report; accepts `ResolveReportRequest` body |

All discover, likes, matches, and notifications queries updated to filter blocked user IDs bidirectionally and exclude soft-deleted users.

---

### `backend/app/routers/authRoutes.py`

- Added `POST /api/auth/restore-account` — public endpoint (no Bearer required); accepts `RestoreAccountRequest`; calls `deletionService.restore_account`; returns 400 for invalid/expired token

---

### `backend/app/main.py`

- Lifespan startup block now calls `await cleanup_expired_deletions()` after index creation; hard-deletes any accounts whose 7-day restore window has elapsed since last restart

---

### `backend/SECURITY_AUDIT_FINAL.md` (new file)

Full OWASP Top 10 (2021) audit. Summary of findings:

| Severity | ID | Finding |
|----------|----|---------|
| High | VULN-01 | `matchRoutes.py` endpoints unauthenticated — already tracked as P3B.2 |
| High | VULN-06 | Password reset token returned in response body — already tracked as P3FT.2 |
| Medium | VULN-02 | No rate limiting on block/report endpoints in router layer (service-layer only for reports) |
| Medium | VULN-03 | No audit log for admin actions |
| Medium | VULN-04 | `cleanup_expired_deletions` runs only at startup — not on a schedule |
| Low | VULN-05 | Sequential integer user IDs enable enumeration — already tracked as P3A.4 |
| Low | VULN-07 | No CSRF protection (mitigated by JSON + Authorization header pattern) |
| Low | VULN-08 | Cloudinary public IDs are sequential — low-entropy |
| Low | VULN-09 | No `Logout` endpoint / token invalidation |
| Low | VULN-10 | `NOTE-2` bulk upload bypasses Pydantic (already open from B3 audit) |

---

### `frontendv2/src/pages/RestoreAccountPage.jsx` (new file)

Public page at `/restore-account`. Accepts a restore token (pre-filled from `?token=` URL param if present). Calls `restoreAccount(token)` from `api.js`. Shows success confirmation on 200 with a link to `/login`; shows error message on 400 (invalid/expired token).

---

### `frontendv2/src/services/api.js`

Seven new exported functions:

| Function | Endpoint |
|----------|---------|
| `blockUser(userId, targetId)` | `POST /users/{userId}/block/{targetId}` |
| `unblockUser(userId, targetId)` | `DELETE /users/{userId}/block/{targetId}` |
| `getBlockedUsers(userId)` | `GET /users/{userId}/blocked` |
| `reportUser(userId, reportedId, payload)` | `POST /users/{userId}/report/{reportedId}` |
| `deleteAccount(userId, payload)` | `DELETE /users/{userId}` |
| `restoreAccount(payload)` | `POST /auth/restore-account` |
| `exportUserData(userId)` | `GET /users/{userId}/export` |

---

### `frontendv2/src/pages/UserDetailPage.jsx`

- **Block button**: confirmation overlay before action; button label toggles between "Block" and "Unblock" based on block state; on block, user is redirected to `/discover`
- **Report button**: opens a modal with a 6-option reason dropdown (`harassment`, `inappropriate_content`, `fake_profile`, `spam`, `underage`, `other`) and an optional description textarea (max 1000 chars); success toast on submit; error message on failure

---

### `frontendv2/src/pages/ProfilePage.jsx`

- **Blocked Users section**: lists all users the current user has blocked; each entry has an Unblock button
- **Danger Zone section** (below blocked users):
  - Export Data button — triggers `exportUserData`; downloads response as `roommatch-data.json`
  - Delete Account button — opens a password modal; on confirm calls `deleteAccount`; displays restore token in a monospace box with a 7-day notice and a link to `/restore-account`
- **Password visibility toggle**: eye icon on the delete account modal password field

---

### `frontendv2/src/App.jsx`

- Added `RestoreAccountPage` import and route at `/restore-account` (outside the auth guard, accessible without a token)

---

### `frontendv2/src/pages/LoginPage.jsx`

- Eye icon toggle on the password field; toggles `type` between `"password"` and `"text"`

---

### `frontendv2/src/pages/SignupPage.jsx`

- Eye icon toggle on the password field (Step 1 of the 3-step wizard)

---

### `frontendv2/src/pages/ResetPasswordPage.jsx`

- Eye icon toggle on the new password field

---

### `frontendAdmin/src/pages/LoginPage.jsx`

- Eye icon toggle on the password field

---

### `backend/tests/helpers.py` (new file)

Provides `AsyncMongoWrapper` — a synchronous-to-async MongoDB wrapper allowing test isolation. Patches all three import sites (`app.database`, `app.routers.authRoutes`, `app.auth.dependencies`) with a test-scoped Motor client backed by the `roommatch_test` DB. Used as the shared fixture foundation for `test_block.py`, `test_report.py`, and `test_deletion.py`.

---

### `backend/tests/test_block.py` (new file)

9 tests across the block system:

| Test | Assertion |
|------|-----------|
| `test_block_user` | Block document created; 200 returned |
| `test_block_already_blocked` | Second block returns 400 |
| `test_unblock_user` | Block document removed; 200 returned |
| `test_block_auto_unmatch` | Match document removed after block |
| `test_blocked_user_hidden_from_discover` | Blocked user absent from top-matches response |
| `test_blocked_user_hidden_from_likes` | Blocked user absent from likes-received response |
| `test_blocked_user_hidden_from_matches` | Blocked user absent from matches response |
| `test_blocked_bidirectional` | Both directions filtered (blocker hidden from blocked too) |
| `test_chat_blocked_403` | `POST /chat/{partner_id}` returns 403 when block exists |

---

### `backend/tests/test_report.py` (new file)

14 tests across the report system:

| Test | Assertion |
|------|-----------|
| `test_create_report` | Report document created; 200 returned |
| `test_report_reason_enum_valid` | All 6 valid reasons accepted |
| `test_report_reason_enum_invalid` | Unknown reason returns 422 |
| `test_report_description_max_length` | 1001-char description returns 422 |
| `test_report_rate_limit` | 6th report in one day returns 429 |
| `test_report_auto_block` | Reporter and reported are blocked after report |
| `test_admin_get_reports_all` | Returns all reports (admin-gated) |
| `test_admin_get_reports_open_filter` | `?status=open` returns only open reports |
| `test_admin_get_reports_resolved_filter` | `?status=resolved` returns only resolved reports |
| `test_admin_get_reports_non_admin_403` | Non-admin user receives 403 |
| `test_admin_resolve_report` | Status set to `resolved`; `resolvedAt` present |
| `test_admin_resolve_nonexistent_404` | Unknown report ID returns 404 |
| `test_resolve_non_admin_403` | Non-admin resolve returns 403 |
| `test_report_self_400` | Reporting yourself returns 400 |

---

### `backend/tests/test_deletion.py` (new file)

15 tests across the deletion system:

| Test | Assertion |
|------|-----------|
| `test_soft_delete` | `deletedAt` set; restore token returned |
| `test_soft_delete_wrong_password` | Wrong password returns 403 |
| `test_soft_deleted_user_hidden_from_discover` | Deleted user absent from discover feed |
| `test_soft_deleted_user_hidden_from_users_all` | Deleted user absent from `GET /users/all` |
| `test_restore_account_valid` | `deletedAt` cleared; account accessible again |
| `test_restore_account_invalid_token` | Unknown token returns 400 |
| `test_restore_account_expired_token` | Expired token returns 400 |
| `test_restore_account_already_active` | Restoring non-deleted account returns 400 |
| `test_export_user_data` | JSON contains profile, likes, matches, messages |
| `test_export_requires_auth` | Unauthenticated export returns 401/403 |
| `test_hard_delete_cascade` | All documents removed from all 7 collections |
| `test_hard_delete_cloudinary` | Cloudinary delete called with correct public ID |
| `test_cleanup_expired` | Accounts older than 7 days hard-deleted on cleanup run |
| `test_cleanup_non_expired` | Accounts within 7-day window not deleted |
| `test_delete_account_endpoint` | Full round-trip: DELETE returns restore token |

---

## Test Results

| Scope | Tests | Result |
|-------|-------|--------|
| New (`test_block.py`) | 9 | All passing |
| New (`test_report.py`) | 14 | All passing |
| New (`test_deletion.py`) | 15 | All passing |
| New (`helpers.py`) | infrastructure | — |
| **New total** | **38** | **38/38 passing** |
| Pre-existing suite | 193 | All passing |
| **Grand total** | **231** | **231/231 passing** |

---

## Open Items / Next Steps

- `cleanup_expired_deletions` runs only at app startup — if the backend is long-running, accounts past their 7-day window are not hard-deleted until the next restart. Should be replaced with APScheduler or an OS-level cron job (tracked as new Phase 3 backlog item).
- VULN-01 (unauthenticated `matchRoutes` endpoints) — already tracked as P3B.2.
- VULN-06 (password reset token in response body) — already tracked as P3FT.2.
- Block/unblock endpoints are not rate-limited at the router layer; only the report endpoint enforces a per-day cap in the service layer. Router-level rate limits should be added.
- The block endpoint path (`/api/users/{id}/block/{target_id}`) should be verified as correctly wired in the frontend — confirm `blockUser` / `unblockUser` in `api.js` are called with the logged-in user's own ID as `id`.

---

## Agents Involved

| Agent | Responsibility |
|-------|----------------|
| Backend Agent | `blockService.py`, `reportService.py`, `deletionService.py`; `database.py`, `models.py`, `dependencies.py`, `userProfileService.py`, `userRoutes.py`, `authRoutes.py`, `main.py` changes |
| Security Audit Agent | Full OWASP Top 10 (2021) audit; `backend/SECURITY_AUDIT_FINAL.md` |
| Frontend Agent (P2.20–P2.22) | `RestoreAccountPage.jsx`, `api.js` additions, `UserDetailPage.jsx` block/report UI, `ProfilePage.jsx` Danger Zone + Blocked Users, `App.jsx` route |
| Frontend Agent (Password Toggle) | Eye icon toggles on `LoginPage`, `SignupPage`, `ResetPasswordPage`, `ProfilePage` (main app), `frontendAdmin` `LoginPage` |
| Tests Agent | `helpers.py`, `test_block.py` (9), `test_report.py` (14), `test_deletion.py` (15) — 38 tests all passing |
| Documentation Agent | This session summary; updated `backend_summary.md`, `frontend_summary.md`, `tests_summary.md`, `TASKS.md` |
