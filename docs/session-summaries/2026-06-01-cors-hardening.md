# Session Summary — 2026-06-01: CORS Hardening (Task C1)

## What changed

CORS configuration in `backend/app/main.py` was changed from a wildcard allow-all to an environment-driven origin allowlist.

**Before:**
```python
allow_origins=["*"]
```

**After:**
```python
allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")]
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allow_headers=["Content-Type", "Authorization"]
```

A CORS rejection test was added at `backend/test_cors.py` covering allowed-origin and disallowed-origin cases.

## Why

Wildcard CORS (`allow_origins=["*"]`) combined with `allow_credentials=True` is a security misconfiguration: it allows any origin to make credentialed cross-site requests to the API. In production this would let an attacker's website silently call authenticated endpoints using a victim's stored token. Scoping CORS to the known frontend origin closes this attack surface.

## Files modified

| File | Change |
|------|--------|
| `backend/app/main.py` | Replaced `allow_origins=["*"]` with `[os.getenv("FRONTEND_URL", "http://localhost:3000")]`; scoped `allow_methods` and `allow_headers` |
| `backend/.env.example` | Added `FRONTEND_URL=http://localhost:3000` |
| `backend/.env` | Added `FRONTEND_URL=http://localhost:3000` (development default) |
| `backend/test_cors.py` | New: verifies allowed-origin receives CORS headers; verifies disallowed-origin does not |

## Env vars added

| Var | Default | Purpose |
|-----|---------|---------|
| `FRONTEND_URL` | `http://localhost:3000` | Single allowed CORS origin; set to the deployed frontend URL in production |

## Action required before production

Set `FRONTEND_URL` to the exact production frontend origin (e.g. `https://roommatch.auburn.edu`). The default `http://localhost:3000` must not be used in production.
