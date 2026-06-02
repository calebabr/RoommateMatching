# Session Summary: Password Security Hardening

**Date:** 2026-05-29
**Project:** RoomMatch
**Focus:** Backend password security improvements prior to beta launch

---

## Overview

This session hardened password handling across the RoomMatch backend, covering hashing strength, input validation, a new change-password endpoint, elimination of latent plaintext exposure risks, and a full password-exposure audit.

---

## Changes Made

### `backend/app/auth/utils.py`

- Raised bcrypt cost factor from 10 (default) to **12** via `bcrypt.gensalt(rounds=12)`.
- Added `MIN_PASSWORD_LENGTH` constant (default `8`, overridable via environment variable).
- Added `validate_password_strength(plain: str) -> None`: enforces minimum length and rejects passwords with a zxcvbn score below 2, returning a user-facing hint on failure.

### `backend/app/routers/authRoutes.py`

- `register()` now calls `validate_password_strength` before hashing; raises HTTP 422 on weak passwords.
- Added `ChangePasswordRequest` Pydantic model.
- Added `POST /api/auth/change-password` endpoint:
  - Requires authentication.
  - Verifies the current password before accepting a change.
  - Validates new password strength via `validate_password_strength`.
  - Rate-limited to 5 requests per hour.
  - Returns `401` for wrong current password, `422` for weak new password.

### `backend/app/services/userProfiles.py`

- Removed plaintext `"password": passW` from legacy `addUser()` dict. This code was unreachable from the API but represented a latent risk.

### `backend/app/routers/userRoutes.py`

- Removed two `traceback.print_exc()` calls from generic exception handlers to prevent stack traces from leaking to logs.

### `backend/app/services/userProfileService.py`

- Added `result.pop("hashed_password", None)` before the return value in `update_profile`, `mark_matched`, and `unmatch_user`, ensuring internal callers never receive the password hash.

### `backend/tests/test_password.py` *(new file)*

13 tests added covering:

- bcrypt round count verification
- Weak password rejection (`password123`, `12345678`, `abc`)
- Strong password acceptance
- HTTP 422 at registration with a weak password
- `401` response on wrong current password at the change-password endpoint
- `422` response on a weak new password at the change-password endpoint
- Happy-path change-password success
- Unauthenticated change-password attempt

---

## Security Audit Results

A password exposure audit was conducted across 14 files (all routers, services, and auth modules).

**Overall result: PASS**

| Check | Result |
|---|---|
| All endpoints strip `hashed_password` before returning user objects | Pass |
| No passwords in logs or error messages | Pass |
| No passwords in URL parameters | Pass |
| Tokens returned only in auth responses | Pass |

---

## Agents Involved

| Agent | Responsibility |
|---|---|
| Auth Agent | Implementation of hashing, validation, and change-password endpoint |
| Backend Agent | Security audit and latent-risk fixes |
| Tests Agent | Test coverage (`test_password.py`) |
