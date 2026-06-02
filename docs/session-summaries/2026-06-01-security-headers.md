# Session Summary — 2026-06-01: Security Headers (Task C2)

## What changed

`SecurityHeadersMiddleware` was added to `backend/app/main.py`, registered after `BodySizeLimitMiddleware`. It injects six HTTP security headers on every response.

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' res.cloudinary.com data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; connect-src 'self'` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

A test file was added at `backend/test_security_headers.py` (1 test, passing).

## Why each header matters

- **Strict-Transport-Security** — instructs browsers to connect only over HTTPS for one year, preventing SSL-stripping attacks.
- **X-Content-Type-Options** — prevents browsers from MIME-sniffing a response away from the declared content type, blocking content-injection via uploaded files.
- **X-Frame-Options** — forbids the app from being embedded in iframes, eliminating clickjacking attack surface.
- **Referrer-Policy** — limits referrer information sent on cross-origin navigations so internal paths are not leaked to third-party sites.
- **Content-Security-Policy** — restricts which origins may load scripts, styles, images, and other resources, reducing XSS impact.
- **Permissions-Policy** — explicitly denies browser feature access (camera, mic, geolocation) that the app never needs.

## CSP tightening path

The current CSP includes `'unsafe-inline'` in `style-src` because frontend components use inline styles via the shared `utils/theme.js` theme object. To drop `'unsafe-inline'`:

1. Move inline style objects from JSX `style={{...}}` props into CSS files or CSS Modules.
2. Remove `'unsafe-inline'` from the `style-src` directive once no inline styles remain.

This is tracked as a future frontend task.

## Files changed

| File | Change |
|------|--------|
| `backend/app/main.py` | Added `SecurityHeadersMiddleware` class and registered it after `BodySizeLimitMiddleware` |
| `backend/test_security_headers.py` | New: 1 test verifying all six headers are present on a response |
