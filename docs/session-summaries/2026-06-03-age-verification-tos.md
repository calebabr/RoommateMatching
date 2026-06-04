# Session Summary: Age Verification and ToS/Privacy Policy (P2.27 + P2.26)

**Date:** 2026-06-03
**Project:** RoomMatch
**Focus:** 18+ age verification at registration and via existing-user gate; Privacy Policy and Terms of Service pages; consent checkbox; ToS versioning for returning users

---

## Overview

Two critical pre-launch compliance tasks were completed. P2.27 adds mandatory age verification (18+) at both registration and via a blocking modal for existing users who lack a `dateOfBirth`. P2.26 adds Privacy Policy and Terms of Service pages, an explicit consent checkbox in the signup flow, and a versioned ToS re-acceptance modal for returning users when the ToS is updated. 12 new backend tests all pass.

---

## Changes

### P2.27 — Age Verification

#### `backend/app/auth/utils.py`

| Change | Detail |
|--------|--------|
| `calculate_age(dob_str: str) -> int` added | Parses `YYYY-MM-DD`; returns integer age in years; raises `ValueError` on bad format |

#### `backend/app/models.py`

| Change | Detail |
|--------|--------|
| `SubmitAgeRequest` added | `dateOfBirth: str` |

#### `backend/app/routers/authRoutes.py`

| Change | Detail |
|--------|--------|
| `RegisterRequest.dateOfBirth` | `Optional[str]`; if provided and age < 18 → HTTP 400; invalid format → HTTP 400; valid 18+ → stored on user document |

#### `backend/app/routers/userRoutes.py`

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `POST /api/users/{user_id}/submit-age` | 5/hour | Auth required; ownership check; under 18 → `is_banned=True` + `ban_reason` + `{"status":"banned",...}`; 18+ → stores `dateOfBirth` + `{"status":"ok"}` |

#### `frontendv2/src/App.jsx`

| Change | Detail |
|--------|--------|
| `AgeGateModal` component added | Full-screen blocking modal; fires when `user.dateOfBirth` is falsy; submits via `submitAge`; shows ban message on banned response |
| `AppRoutes` early-return order | age gate → ToS modal → normal routes |

#### `frontendv2/src/pages/SignupPage.jsx`

| Change | Detail |
|--------|--------|
| `dateOfBirth` date input | Step 0, after Username field; client-side age check blocks under-18 before API call |
| `dateOfBirth` in signup payload | Sent to `authRegister` |

#### `frontendv2/src/services/api.js`

| Function | Endpoint |
|----------|----------|
| `submitAge(userId, dateOfBirth)` | `POST /users/{userId}/submit-age` |

#### `backend/tests/test_age_verification.py` (new file)

12 tests:

| Test | Behavior Verified |
|------|------------------|
| Register with adult DOB | 200, `dateOfBirth` stored |
| Register underage | 400 rejected |
| Register without DOB | 200, proceeds |
| Submit-age adult | 200, `{"status":"ok"}`, `dateOfBirth` stored |
| Submit-age underage | 200, `{"status":"banned"}`, `is_banned=True` |
| Submit-age unauthenticated | 401 |
| Submit-age wrong user | 403 |
| Invalid date format | 400 |
| Banned user cannot login | 403 |
| Exactly-18 passes | 200 ok |
| Register invalid DOB format | 400 |

---

### P2.26 — Privacy Policy, Terms of Service, Consent, and Versioning

#### `backend/app/models.py`

| Change | Detail |
|--------|--------|
| `AcceptTermsRequest` added | `termsVersion: str` |

#### `backend/app/routers/authRoutes.py`

| Change | Detail |
|--------|--------|
| `RegisterRequest.termsVersion` | `Optional[str]`; when provided, stores `termsVersion` + `termsAcceptedAt` (UTC ISO) on user document |

#### `backend/app/routers/userRoutes.py`

| Endpoint | Rate limit | Behavior |
|----------|-----------|---------|
| `POST /api/users/{user_id}/accept-terms` | 10/hour | Auth required; ownership check; stores `termsVersion` + `termsAcceptedAt`; returns `{"status":"ok"}` |

#### `frontendv2/src/styles/LegalPage.css` (new file)

Shared CSS for both legal pages. Dark theme with `#E8A838` headings and `#1A1A1A` card sections.

#### `frontendv2/src/pages/PrivacyPolicyPage.jsx` (new file)

8-section Privacy Policy at `/privacy`. Covers: data collection, storage, third-party services (Cloudinary, SendGrid, Sentry, PostHog, Atlas, Render, Vercel), data retention, GDPR portability and deletion rights.

#### `frontendv2/src/pages/TermsOfServicePage.jsx` (new file)

10-section Terms of Service at `/terms`. Covers: eligibility, acceptable use, content ownership, DMCA, privacy, dispute resolution/arbitration, limitation of liability, and termination.

#### `frontendv2/src/pages/SignupPage.jsx`

| Change | Detail |
|--------|--------|
| `agreedToTerms` checkbox | Unchecked by default; links to `/terms` and `/privacy`; blocks signup submission until checked |
| `termsVersion` in payload | `"2026-06-03"` sent to `authRegister` |

#### `frontendv2/src/services/api.js`

| Function | Endpoint |
|----------|----------|
| `acceptTerms(userId, termsVersion)` | `POST /users/{userId}/accept-terms` |

#### `frontendv2/src/App.jsx`

| Change | Detail |
|--------|--------|
| `CURRENT_TERMS_VERSION = "2026-06-03"` | Module-level constant; bump to trigger re-acceptance for all users |
| `TERMS_CHANGELOG` | Array of change descriptions shown in the ToS modal banner |
| `ToSModal` component | Blocking modal; fires when user's `termsVersion` !== `CURRENT_TERMS_VERSION`; shows changelog banner; checkbox guard before "Accept & Continue"; calls `acceptTerms` on confirm |
| `/privacy` and `/terms` routes | Added outside the auth guard (public access) |

---

## Test Results

| File | Tests | Result |
|------|-------|--------|
| `backend/tests/test_age_verification.py` | 12 | All passing |
| Pre-existing suite | 240 | All passing |
| **Total** | **252** | **252/252 passing** |

---

## Open Items / Next Steps

- **No tests for P2.26 accept-terms endpoint** — the endpoint follows the same auth/ownership pattern as submit-age; coverage is low-priority but should be added alongside any future ToS-versioning tests.
- **Lawyer review deferred to P4.2** — the Privacy Policy and Terms of Service were drafted programmatically and cover standard clauses. A legal review for FERPA compliance (student data), COPPA compliance (age verification), and arbitration enforceability is tracked as P4.2 before campus-wide launch.
- **Age gate modal has no email delivery** — when an existing user is auto-banned for being under 18, the ban is silent beyond the in-app message. An email notification (tracked under future SendGrid integration) would improve the experience.

---

## Agents Involved

| Agent | Responsibility |
|-------|----------------|
| Backend Agent | `calculate_age` helper, `SubmitAgeRequest`/`AcceptTermsRequest` models, `dateOfBirth`/`termsVersion` at register, `submit-age` and `accept-terms` endpoints |
| Frontend Agent | `AgeGateModal`, `ToSModal`, `dateOfBirth` + `agreedToTerms` in `SignupPage`, `submitAge`/`acceptTerms` in `api.js`, `PrivacyPolicyPage`, `TermsOfServicePage`, `LegalPage.css`, public routes |
| Tests Agent | `test_age_verification.py` (12 tests) |
| Documentation Agent | This session summary, updated `frontend_summary.md`, `backend_summary.md`, `tests_summary.md`, `TASKS.md` |
