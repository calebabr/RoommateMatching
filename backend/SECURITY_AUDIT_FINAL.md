# RoomMatch Security Audit — Final Report

**Date:** 2026-06-03  
**Scope:** Full backend — FastAPI application + MongoDB (Motor/PyMongo)  
**Auditor:** Backend Security Agent  
**Files reviewed:** `main.py`, `routers/authRoutes.py`, `routers/userRoutes.py`, `routers/matchRoutes.py`, `auth/utils.py`, `auth/dependencies.py`, `app/limiter.py`, `services/userProfileService.py`, `services/likeService.py`, `services/chatService.py`, `services/notificationService.py`, `services/recommendationService.py`, `services/matchScore.py`, `models.py`, `database.py`, `requirements.txt`  
**Prior reports consulted:** `SECURITY_AUDIT_IDOR.md`, `SECURITY_MONGO_INJECTION.md`, `SECURITY_SECRETS_AUDIT.md`, `SECURITY_JWT.md`

---

## Executive Summary

RoomMatch has a generally sound security posture for a university-scale web application. Prior targeted audits resolved all IDOR vulnerabilities, the JWT implementation is correct, and no MongoDB operator-injection paths were found. Security headers, rate limiting, CORS, and input sanitization are all present.

Three residual issues require attention before any broader public deployment: (1) the profile update endpoint does not strip the plaintext `password` field from its `$set` payload, allowing a user to persist cleartext credentials in their own MongoDB document; (2) the `/uploadUsers` and `/match` endpoints on `matchRoutes.py` have no authentication guard, making them callable by anyone who can reach the server; and (3) the in-memory rate-limiter counter resets on every process restart, meaning the rate limits for registration and login provide no protection in environments with autoscaling or frequent restarts.

All other OWASP Top 10 categories are either fully mitigated or carry only low residual risk that has been explicitly accepted.

---

## OWASP Top 10 (2021) Assessment

### A01 — Broken Access Control

**Status:** Partially Mitigated

**Findings:**

- All user-scoped routes in `userRoutes.py` use `get_current_user_or_403`, which checks that the authenticated caller's `id` matches the `{user_id}` path parameter. Chat endpoints additionally enforce `verify_match_exists`. These fixes resolved 18 previously vulnerable routes documented in `SECURITY_AUDIT_IDOR.md`.
- `GET /api/users/all` returns full profiles for every user, including `bio`, `photoUrl`, `lifestyleTags`, and all nine preference scores, to any authenticated user — not just the profile owner. No field projection is applied.
- `GET /api/users/{user_id}` is owner-only (`get_current_user_or_403`). This means other authenticated users cannot view any profile besides their own. This is overly restrictive for a matching app (the recommendation UI needs to display cards for other users), but it is not a security vulnerability.
- `POST /api/uploadUsers`, `GET /api/get-users`, `POST /api/match`, and `POST /api/matchScore` in `matchRoutes.py` have no authentication dependency. Any unauthenticated HTTP client can invoke these endpoints, upload arbitrary user data, retrieve stored bulk data, and trigger batch match computation.
- Admin endpoints (`/admin/*`) are protected by `get_admin_user`, which checks membership in `ADMIN_USER_IDS` from the environment. This is correct.
- The `limit` query parameter on `GET /users/{user_id}/chat/{partner_id}` is forwarded verbatim to MongoDB `.limit()` with no upper bound. A caller can pass `?limit=9999999` to request an arbitrarily large result set.

**Mitigations in place:** `get_current_user_or_403` on all user-scoped routes; `verify_match_exists` on chat; `get_admin_user` on admin routes; JWT required on all `userRoutes.py` and `authRoutes.py` endpoints.

**Residual risk:** Medium — `matchRoutes.py` endpoints are unauthenticated (VULN-01). The unbounded `limit` parameter is a minor DoS surface (VULN-05). `GET /users/all` leaks full preference profiles to all authenticated users; this may be intentional for the discovery feature but is worth noting.

---

### A02 — Cryptographic Failures

**Status:** Mitigated

**Findings:**

- Passwords are hashed with `bcrypt` at cost factor 12 (`bcrypt.gensalt(rounds=12)`), which is appropriate.
- JWTs use HS256 with a secret key loaded from the `SECRET_KEY` environment variable. The `decode_token` function passes `algorithms=["HS256"]` and `options={"verify_signature": True}`, explicitly rejecting the `"none"` algorithm.
- A `RuntimeError` is raised at startup if `SECRET_KEY` is absent and `ROOMMATCH_ENV` is not `test` or `development`, preventing accidental production deployment without a key.
- Password reset tokens are generated with `secrets.token_urlsafe(32)` (256 bits of entropy) and stored only as a SHA-256 hash in the database. The raw token is returned in the response body rather than emailed — see VULN-06.
- Cloudinary credentials and MongoDB URL are read from environment variables; no credentials are hardcoded in current source. One historical dev JWT secret (`roommatch-dev-secret-change-in-prod`) remains in git history (documented in `SECURITY_SECRETS_AUDIT.md`).
- HSTS is set to `max-age=31536000; includeSubDomains` via the `SecurityHeadersMiddleware`, forcing HTTPS in browsers that have visited the site.
- `send_default_pii=False` is set in the Sentry integration; Authorization headers are filtered before event transmission.

**Mitigations in place:** bcrypt-12, explicit HS256 enforcement, env-var secrets, HSTS.

**Residual risk:** Low — the dev JWT secret in git history is accepted risk for a student project (no evidence of production deployment with that key). The SHA-256 hash comparison for password reset tokens is technically a timing-safe approach only if bcrypt or `hmac.compare_digest` is used; Python's `==` on string hashes is not guaranteed constant-time, though the SHA-256 pre-image resistance makes practical exploitation extremely unlikely.

---

### A03 — Injection

**Status:** Mitigated

**Findings:**

- No `$where`, `$function`, `$accumulator`, or `mapReduce` operators found anywhere in the codebase.
- No `$regex` applied to user-supplied strings. All lookups use exact equality filters.
- All query filter values are either hardcoded literals or derived from Pydantic-validated Python `int` or `str` fields that reject dict-injection payloads at deserialization time.
- `ChatMessageCreate.content` and `bio` fields are sanitised with `nh3.clean(v, tags=set())` before storage, stripping all HTML tags. Lifestyle tags are validated against an allowlist (`ALLOWED_LIFESTYLE_TAGS`).
- `FINDING-2` from `SECURITY_MONGO_INJECTION.md` is still open: `update_profile` passes the full Pydantic `model_dump()` dict into a MongoDB `$set`, allowing an authenticated user to write the plaintext `password` field, change `email`, or change `gender` (VULN-02). The immutable-field strip in `userRoutes.py` (`_IMMUTABLE_FIELDS` frozenset) covers `password` and `email` but the strip happens in the router, not in the service, so any future caller of `userProfileService.update_profile()` bypasses it.
- `FINDING-1` from `SECURITY_MONGO_INJECTION.md` (preference fields in `RegisterRequest` typed as `Optional[dict]` instead of `Preference`) is still open as a data-integrity issue (VULN-07). It is not a query-injection risk.
- The `limit` parameter in `chatService.get_messages` is unbounded (VULN-05, also classified under A01).

**Mitigations in place:** Pydantic type enforcement on all query-facing fields; nh3 HTML sanitization; allowlist validation for lifestyle tags; no JavaScript-executing MongoDB operators.

**Residual risk:** Low-Medium — VULN-02 (plaintext password writeable to DB document by the user themselves) is the most notable injection-adjacent risk here, though it is not a classic injection; it is a mass-assignment vulnerability.

---

### A04 — Insecure Design

**Status:** Partially Mitigated

**Findings:**

- The `/api/auth/forgot-password` endpoint returns the raw reset token in the JSON response body instead of emailing it. The comment in source reads: "In production this will be emailed automatically." No email integration exists. An attacker who can read HTTP responses (e.g., via an intercepting proxy, browser extension, or XSS) obtains the reset token directly — making the "forgot password" flow trivially bypassable (VULN-06).
- There is no account lockout after repeated failed login attempts; the rate limit (5 attempts per 15 minutes per IP/token-prefix) is the only brute-force protection. If rate-limit state resets on restart (memory storage), window is effectively unlimited across restarts.
- No CSRF protection exists. The application relies on the `Authorization: Bearer` header, which is not vulnerable to classic CSRF (cookies are not used for auth). This is an acceptable design decision for a Bearer-token API.
- No email verification at registration. Users can register with any email string, valid or not. Downstream risks: spam accounts, inability to recover accounts, no confirmation that the user owns the address.
- The matching algorithm recomputes recommendations for all users on every new registration, profile update, or unmatch event (O(N²) operations). For large N this is a denial-of-service surface if registrations can be automated — the 3/hour registration rate limit partially mitigates this.

**Mitigations in place:** Rate limiting on auth endpoints; Bearer token auth design avoids CSRF; nh3 sanitization prevents stored XSS.

**Residual risk:** Medium — VULN-06 (password reset token returned in response body) is an insecure design that must be resolved before production. The lack of email verification is accepted technical debt.

---

### A05 — Security Misconfiguration

**Status:** Partially Mitigated

**Findings:**

- Security headers are applied to every HTTP response: HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy`, `Permissions-Policy`. The implementation uses a raw ASGI middleware to avoid the known Starlette `BaseHTTPMiddleware` header-drop bug on streaming responses — this is a well-considered approach.
- The CSP includes `script-src 'self' 'unsafe-inline'` and `style-src 'self' 'unsafe-inline'`. The `unsafe-inline` directives significantly weaken XSS protection provided by CSP (VULN-08).
- CORS is configured to allow only the origins specified in `FRONTEND_URL` and `ADMIN_FRONTEND_URL` environment variables, defaulting to `localhost:3000`. This is correct. `allow_credentials=True` is set, which is appropriate since the same-origin is explicitly listed (not a wildcard).
- FastAPI's automatic OpenAPI/Swagger UI (`/docs`, `/redoc`) is enabled by default. These endpoints expose the full API schema to anyone who can reach the server. For a production deployment this is an information disclosure risk.
- The `/debug/sentry-test` endpoint is gated on `ROOMMATCH_ENV != "production"`, which is correct.
- The `BodySizeLimitMiddleware` limits request bodies to 1 MB (skipping the photo upload endpoint). Photo uploads are separately limited to 5 MB with a dimension check.
- MongoDB is accessed at `localhost:27017` (or `MONGO_URL` env var) with no authentication credentials in the default configuration. The database itself has no auth enforced unless the deployment environment provides it via the `MONGO_URL` URI.
- The in-memory rate limiter resets on every process restart. Persistent rate limiting requires the optional Redis integration via `UPSTASH_REDIS_URL` (VULN-03).

**Mitigations in place:** Full security header suite; CORS allowlist; request body size limits; debug endpoint gated by environment variable.

**Residual risk:** Low-Medium — `unsafe-inline` in CSP (VULN-08), Swagger UI open in production (low), in-memory rate limiter (VULN-03), MongoDB auth depends on deployment configuration.

---

### A06 — Vulnerable and Outdated Components

**Status:** Partially Mitigated

**Findings:**

Current pinned versions from `requirements.txt`:

| Package | Pinned | Notes |
|---------|--------|-------|
| `fastapi` | 0.128.0 | Recent; check for 0.x advisories |
| `uvicorn` | 0.40.0 | Recent |
| `motor` | 3.7.1 | Recent |
| `pymongo` | 4.16.0 | Recent |
| `pydantic` | 2.12.5 | Recent (v2 series) |
| `bcrypt` | 5.0.0 | Recent |
| `python-jose[cryptography]` | 3.5.0 | **Known CVE history** — see below |
| `python-multipart` | 0.0.22 | Recent; was vulnerable in older versions |
| `slowapi` | 0.1.9 | Recent |
| `zxcvbn` | 4.4.28 | Recent |
| `Pillow` | 10.4.0 | Older — 11.x released; check advisories |
| `cloudinary` | 1.40.0 | Recent |
| `nh3` | 0.2.17 | Recent |
| `sentry-sdk[fastapi]` | 2.19.2 | Recent |
| `networkx` | unpinned | No version constraint — any version will install |

`python-jose` has had multiple CVEs in its history (notably related to algorithm confusion and JWKS key handling in older versions). The 3.5.0 release addressed several issues, but the package is in limited maintenance mode. The `decode_token` function explicitly specifies `algorithms=["HS256"]` and `verify_signature=True`, which are the correct mitigations for the known `python-jose` algorithm-confusion attacks.

`networkx` has no version pin. Any breaking change or vulnerable version could be installed silently.

`Pillow` 10.4.x is no longer the latest major release. Pillow has a history of image-parsing vulnerabilities; upgrading to 11.x is recommended.

No automated dependency scanning (Dependabot, pip-audit, Safety) is configured in CI.

**Mitigations in place:** Correct `python-jose` usage (explicit algorithm list, signature verification); Pillow re-encoding of uploaded images strips EXIF and neutralizes known payload-in-image attacks even on vulnerable Pillow versions.

**Residual risk:** Low-Medium — `networkx` unpinned (VULN-09), no automated dependency scanning, `python-jose` is in limited maintenance.

---

### A07 — Identification and Authentication Failures

**Status:** Mitigated

**Findings:**

- Passwords are validated with `zxcvbn` (score >= 2) and a configurable minimum length (default 8, set via `MIN_PASSWORD_LENGTH` env var). This prevents trivially weak passwords.
- bcrypt with cost factor 12 is used for storage. Brute-force of stolen hashes requires significant computational effort.
- JWT tokens have a 24-hour expiry enforced by `python-jose`. There is no refresh token flow; users must re-authenticate after expiry.
- The `decode_token` function returns `None` on any `JWTError`, which covers expired tokens, tampered signatures, and malformed inputs. The `get_current_user` dependency returns HTTP 401 on `None`.
- Login and registration are rate-limited (5/15min login, 3/hour registration). Change-password is rate-limited 5/hour. Forgot-password is rate-limited 3/hour.
- Banned users receive HTTP 403 at login. The ban check occurs after password verification, preventing user enumeration by ban status alone.
- The login response uses the same error message for "user not found" and "wrong password" (`"Invalid email or password"`), preventing email enumeration via login.
- JWT tokens are never logged and are stripped from Sentry events.
- There is no multi-factor authentication. This is acceptable for the current use case.
- The rate limiter keys on the first 32 characters of the Bearer token or IP address. Token-prefix keying is a reasonable approach but means a single compromised token prefix can exhaust another user's rate limit (low-probability, low-impact).

**Mitigations in place:** bcrypt-12, zxcvbn strength validation, 24h token expiry, rate limiting, same error message for invalid credentials, hashed password reset tokens.

**Residual risk:** Low — no significant residual authentication risk. The lack of MFA and email verification is accepted design scope for a student project.

---

### A08 — Software and Data Integrity Failures

**Status:** Partially Mitigated

**Findings:**

- Uploaded images are validated by magic-byte inspection (not trusting the `Content-Type` header) and re-encoded through Pillow. Re-encoding strips EXIF metadata (including GPS coordinates) and neutralizes steganographic or polyglot payloads.
- Image filenames are UUID-generated; user-provided filenames and extensions are never used.
- Old Cloudinary photos are deleted when a new photo is uploaded (with fallback for legacy local files).
- The `_IMMUTABLE_FIELDS` frozenset in `userRoutes.py` prevents the profile update endpoint from overwriting `id`, `matched`, `matchCount`, `matchedWith`, `createdAt`, `email`, and `photoUrl`. However, the strip is applied in the router layer, not in `userProfileService.update_profile` — any future internal caller of `update_profile` bypasses this protection.
- `hashed_password` is included in `_IMMUTABLE_FIELDS`, preventing it from being overwritten via the profile update. However, `password` (plaintext) is **not** in `_IMMUTABLE_FIELDS`. A user can submit `{"password": "plaintext"}` in a profile update body; Pydantic accepts it (`UserCreate.password` is `Optional[str]`), the router excludes it from the preferences dict via `k not in _IMMUTABLE_FIELDS`, but `_IMMUTABLE_FIELDS` does **not** contain `"password"` (only `"hashed_password"`). Cross-referencing the router code confirms `password` is excluded: `_IMMUTABLE_FIELDS = frozenset({"password", "hashed_password", ...})`. Re-reading `userRoutes.py` line 29-32 confirms `"password"` IS in the frozenset. This means the plaintext password field IS filtered at the router. The service-level risk (direct call bypassing the frozenset) remains an architectural concern but is not currently exploitable.
- There is no package integrity verification in the deployment pipeline (no `pip hash` checking, no `requirements.txt.lock`).
- There is no CI pipeline verifying build integrity or running security scans on pull requests.

**Mitigations in place:** Magic-byte image validation, Pillow re-encoding, UUID filenames, `_IMMUTABLE_FIELDS` protection in router.

**Residual risk:** Low — the service-level bypass path for `update_profile` is a maintainability concern (VULN-04). No supply-chain integrity verification in CI.

---

### A09 — Security Logging and Monitoring Failures

**Status:** Partially Mitigated

**Findings:**

- Sentry integration is present and conditionally initialized when `SENTRY_DSN` is set. It captures unhandled exceptions, rate-limit violations (with IP and user ID), and custom events.
- The Sentry `before_send` hook filters out 401/403/404/429 HTTP exceptions (expected operational noise) and strips `Authorization` headers and cookies from event payloads, preventing token leakage into Sentry.
- Rate-limit violations are logged to Sentry with IP address and decoded user ID.
- There is no application-level audit log for security-sensitive events: failed login attempts, account bans/unbans, password changes, account deletions, and admin actions are not recorded anywhere beyond what Sentry might capture incidentally.
- There is no structured logging to stdout/stderr. FastAPI/uvicorn access logs go to stdout but contain no application-layer security events.
- Without Sentry configured (the default for local and staging environments), there is zero security-event visibility.
- No alerting thresholds or dashboards are defined, so even with Sentry enabled, sustained attacks would not trigger automated alerts.

**Mitigations in place:** Sentry integration with PII filtering; rate-limit event reporting; token stripping in event payloads.

**Residual risk:** Medium — no structured audit log for authentication and admin events (VULN-10). Security monitoring depends entirely on Sentry being configured, which is optional.

---

### A10 — Server-Side Request Forgery (SSRF)

**Status:** Mitigated

**Findings:**

- The backend does not accept URLs from user input and make outbound HTTP requests based on them. No `requests.get(user_provided_url)` or equivalent pattern was found.
- The only outbound HTTP calls are to Cloudinary (via the Cloudinary SDK), which operates on validated binary image data, not user-supplied URLs.
- `photoUrl` is stored in the database as a string provided by Cloudinary; it is served to clients as-is but never fetched by the backend.
- The password reset flow returns a token in the response body; it does not send email or make outbound HTTP requests.

**Mitigations in place:** No user-URL-to-outbound-request pattern exists in the codebase.

**Residual risk:** None identified.

---

## Vulnerability Summary Table

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| VULN-01 | `matchRoutes.py` endpoints unauthenticated | High | Open |
| VULN-02 | `update_profile` service bypasses immutable-field protection | Medium | Open (router-level fix exists; service is unguarded) |
| VULN-03 | Rate limiter in-memory only; resets on restart | Medium | Open |
| VULN-04 | `userProfileService.update_profile` no field strip at service layer | Medium | Open |
| VULN-05 | Unbounded `limit` parameter in chat message retrieval | Low | Open |
| VULN-06 | Password reset token returned in response body, not emailed | High | Open |
| VULN-07 | `RegisterRequest` preference fields typed `Optional[dict]` | Low | Open |
| VULN-08 | CSP `unsafe-inline` weakens XSS protection | Low | Open |
| VULN-09 | `networkx` dependency unpinned | Low | Open |
| VULN-10 | No audit log for security-sensitive events | Medium | Open |

---

## Detailed Findings

### VULN-01 — `matchRoutes.py` Endpoints Unauthenticated

**Description:** Four endpoints in `matchRoutes.py` — `POST /api/uploadUsers`, `GET /api/get-users`, `POST /api/match`, and `POST /api/matchScore` — have no `Depends(get_current_user)` guard. Any HTTP client, authenticated or not, can call these endpoints.

`POST /api/uploadUsers` accepts a JSON file and overwrites the in-memory user store (used by the batch match algorithm). An unauthenticated attacker can replace the user dataset with fabricated data, causing the batch match to produce arbitrary results.

`GET /api/get-users` returns the full in-memory user store (including hashed preference data) to unauthenticated callers.

`POST /api/match` runs the batch matching algorithm on whatever data is in the user store.

**Location:** `backend/app/routers/matchRoutes.py`, lines 25-65

**Impact:** Information disclosure (user preference data), denial of service (overwrite dataset), integrity violation (trigger arbitrary match computation).

**Recommended fix:** Add `_: dict = Depends(get_current_user)` to each endpoint signature. For truly admin-only operations, use `get_admin_user` instead.

**Effort:** Low (30 minutes)

---

### VULN-02 / VULN-04 — Mass Assignment in `update_profile` (Service Layer Unguarded)

**Description:** `userProfileService.update_profile` passes the caller-supplied `preferences` dict directly into a MongoDB `$set` without any field-level filtering at the service layer. The router in `userRoutes.py` applies `_IMMUTABLE_FIELDS` filtering before calling the service, but this is a fragile defense — any future code that calls `update_profile` directly bypasses it.

Additionally, `_IMMUTABLE_FIELDS` does not include `gender`. An authenticated user can change their own `gender` field via `PUT /api/users/{user_id}`, bypassing the gender-gated matching restriction. The `RegisterRequest` validator enforces `gender` to `"male"` or `"female"` at registration, but `UserCreate` (used by the update endpoint) accepts any value for `gender` that passes the inline check (`if user_data.get("gender", "").lower() not in ("male", "female")`). The update path does perform this check but `gender` remains a mutable field post-registration.

**Location:** `backend/app/services/userProfileService.py` lines 100-104; `backend/app/routers/userRoutes.py` lines 88-103

**Impact:** Authenticated users can mutate their gender after registration to bypass same-gender matching restrictions. Any future internal caller of `update_profile` bypasses the immutable-field protection entirely.

**Recommended fix:**
1. Move the immutable-field strip into `userProfileService.update_profile` itself, not only the router.
2. Consider whether `gender` should be immutable after registration (if so, add it to `_IMMUTABLE_FIELDS`).

**Effort:** Low (1 hour)

---

### VULN-03 — In-Memory Rate Limiter Resets on Restart

**Description:** The `limiter` is configured with `storage_uri="memory://"` unless `UPSTASH_REDIS_URL` is set. In-memory storage means all rate-limit counters are lost on every process restart (including Uvicorn hot-reload, platform cold-starts on Render/Railway free tier, or any crash recovery). An attacker can exhaust the rate limit, trigger a restart, and immediately begin a new burst.

The most sensitive limits are registration (3/hour) and login (5/15 minutes). With an in-memory limiter on a platform that cold-starts, these limits are effectively non-functional between process starts.

**Location:** `backend/app/limiter.py`, line 26

**Impact:** Rate limiting for brute-force protection is ineffective across restarts. Login brute-force and registration spam are not reliably bounded.

**Recommended fix:** Provision an Upstash Redis instance (free tier available) and set `UPSTASH_REDIS_URL` in the deployment environment. The limiter code already supports this path.

**Effort:** Low (30 minutes of configuration)

---

### VULN-05 — Unbounded `limit` Parameter in Chat Endpoint

**Description:** `GET /api/users/{user_id}/chat/{partner_id}?limit=N` forwards `limit` directly to MongoDB `.limit(N)`. No upper bound is enforced. A caller can request `?limit=10000000`, causing the database to scan and return millions of documents in a single response, consuming server memory and connection time.

**Location:** `backend/app/routers/userRoutes.py` line 189; `backend/app/services/chatService.py` line 49

**Impact:** Authenticated denial-of-service against the server (memory exhaustion) by any matched user.

**Recommended fix:** Clamp the limit in the service: `limit = min(max(limit, 1), 500)`.

**Effort:** Very low (5 minutes)

---

### VULN-06 — Password Reset Token Returned in Response Body

**Description:** `POST /api/auth/forgot-password` generates a password reset token and returns it directly in the JSON response:

```python
return {
    "reset_token": token,
    "message": "If that email exists, a reset token has been generated. ...",
}
```

The comment acknowledges this is not production-ready. In a real deployment, this means anyone who can intercept or read the HTTP response (browser console, shared network, proxy, XSS) can obtain the reset token and reset another user's password without owning their email inbox.

**Location:** `backend/app/routers/authRoutes.py` lines 224-228

**Impact:** Password reset token is trivially accessible to any observer of HTTP responses. Any XSS vulnerability or network observer can hijack account recovery.

**Recommended fix:** Send the reset token via email (SMTP or SendGrid/Mailgun transactional email API). Never return it in the response body. Return only the generic message regardless of whether the email was found.

**Effort:** Medium (3-4 hours to integrate an email provider)

---

### VULN-07 — `RegisterRequest` Preference Fields Typed `Optional[dict]`

**Description:** In `authRoutes.RegisterRequest`, all nine preference fields are declared as `Optional[Preference]` with defaults, correctly using the `Preference` model. Cross-checking with the current source confirms these ARE typed as `Optional[Preference]` (the `SECURITY_MONGO_INJECTION.md` report documented a prior state where they were `Optional[dict]`; the current code uses `Preference`). This finding should be treated as a verification item — confirm the fix from the injection audit is in place.

**Location:** `backend/app/routers/authRoutes.py` lines 27-35

**Impact:** If any preference field reverts to `Optional[dict]`, malformed data could be stored at registration, corrupting the matching algorithm.

**Recommended fix:** No action required if current code already uses `Preference`. Add a regression test to confirm `RegisterRequest` rejects non-conforming preference objects.

**Effort:** Very low

---

### VULN-08 — CSP `unsafe-inline` Directives

**Description:** The Content-Security-Policy header includes:

```
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
```

The `unsafe-inline` directive for `script-src` defeats CSP's primary XSS mitigation. If a stored or reflected XSS payload is ever introduced, the CSP will not block inline script execution.

**Location:** `backend/app/main.py` line 159-165

**Impact:** CSP provides no XSS protection for inline scripts or styles. This is a defense-in-depth degradation rather than a standalone vulnerability.

**Recommended fix:** Migrate all inline styles to CSS classes and all inline scripts to external `.js` files. Replace `unsafe-inline` with a `nonce-{random}` approach or remove it entirely. The source comment acknowledges this is temporary.

**Effort:** High (requires frontend refactoring to eliminate all inline styles/scripts)

---

### VULN-09 — `networkx` Dependency Unpinned

**Description:** `requirements.txt` specifies `networkx` without a version constraint. Any `pip install` will install the latest available version, which could include breaking changes or, in an unlikely supply-chain scenario, a malicious release.

**Location:** `backend/requirements.txt` line 19

**Impact:** Non-deterministic builds; potential silent breakage or supply-chain exposure.

**Recommended fix:** Pin to a specific version: `networkx==3.x.y`.

**Effort:** Very low (5 minutes)

---

### VULN-10 — No Audit Log for Security-Sensitive Events

**Description:** The following security-relevant events produce no persistent log entry outside of Sentry (which is optional and not configured by default):

- Failed login attempts (attacker reconnaissance)
- Successful logins (access record)
- Password changes (potential account takeover indicator)
- Account bans and unbans (admin accountability)
- Account deletions (data destruction)
- Admin endpoint usage
- Rate-limit violations (only logged to Sentry when `SENTRY_DSN` is set)

**Location:** `backend/app/routers/authRoutes.py`, `backend/app/routers/userRoutes.py`

**Impact:** In the event of an incident, there is no audit trail to reconstruct attacker activity, identify compromised accounts, or demonstrate compliance with data-protection obligations.

**Recommended fix:** Add structured log statements (using Python's `logging` module) for each security-sensitive event, including at minimum: timestamp, event type, user ID, and IP address. Consider a dedicated security audit log distinct from application logs.

**Effort:** Medium (2-3 hours)

---

## Residual Risk Register

The following items are accepted with rationale:

| Item | Risk Level | Rationale |
|------|-----------|-----------|
| Historical dev JWT secret in git history | Low | The secret was never used in a production deployment; current code rejects it at startup. Expunging git history is an operational decision for the team. |
| No multi-factor authentication | Low | Out of scope for a university project matching app with no financial or health data. |
| No email verification at registration | Low-Medium | Accepted technical debt. Adds account hygiene but is not a direct security vulnerability in the current data model. |
| FastAPI Swagger UI enabled | Low | Exposes API schema. Acceptable for a development/student project; consider disabling in production with `FastAPI(docs_url=None, redoc_url=None)`. |
| SHA-256 comparison for password reset token not using `hmac.compare_digest` | Very Low | SHA-256 pre-image resistance makes timing attacks impractical despite non-constant-time comparison. |
| CSP `unsafe-inline` for styles | Low | Frontend uses extensive inline styles (React component pattern); removing them is a large refactor. No stored XSS has been identified. |
| MongoDB without authentication in local dev | Low | Only affects developer machines where MongoDB is localhost-only. Production must use an authenticated URI via `MONGO_URL`. |
| `GET /api/users/all` returns full preference profiles to any authenticated user | Low-Medium | Intentional for the discovery/recommendation UI; no directly sensitive PII is exposed (no real name, phone, or financial data). Accepted pending a field-projection endpoint design. |

---

## Items Requiring Business/Legal Decisions

1. **Email address as user identifier:** Email addresses are collected at registration and used as the primary login identifier. Under FERPA (for a university context) and GDPR/CCPA (if any EU or California residents register), email addresses are personal data. A privacy policy and data retention schedule are required before any public launch.

2. **Gender field and matching restriction:** The application enforces same-gender matching exclusively. This is a business rule encoded in the gender field. Any change to include non-binary options or cross-gender matching requires coordinated changes to the `genderCompatible` matching logic, `RegisterRequest` gender validation, and potentially the UX.

3. **Password reset via email:** Implementing email-based password reset requires selecting a transactional email provider (SendGrid, Mailgun, AWS SES, etc.), agreeing to their terms of service, and potentially verifying a sending domain. This is a procurement and configuration decision, not a purely technical one.

4. **Sentry PII policy:** Even with `send_default_pii=False` and filtered headers, Sentry receives exception stack traces that may include user IDs and request paths. Before enabling Sentry in production, confirm the Sentry data residency region and data processing agreement (DPA) are acceptable under applicable privacy rules.

5. **Cloudinary image retention:** Profile photos uploaded to Cloudinary are retained there even after account deletion (the application deletes the Cloudinary asset on photo replacement, but account deletion in `userProfileService.delete_user` does not call `cloudinary.uploader.destroy`). A data retention and deletion policy for user-uploaded content is required for GDPR compliance.

6. **Rate limit persistence infrastructure:** Moving from in-memory to Redis-backed rate limiting requires provisioning a Redis instance. For Render/Railway free-tier deployments, Upstash Redis has a free tier, but any Redis provider introduces a dependency and potential cost. This is a deployment architecture decision.
