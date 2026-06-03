# JWT Security Reference

## SECRET_KEY Management

- Loaded exclusively from the `SECRET_KEY` environment variable (`backend/app/auth/utils.py`)
- Raises `RuntimeError` at startup if not set (except when `ROOMMATCH_ENV=test` or `ROOMMATCH_ENV=development`)
- Never hardcoded in source code
- Generate a production secret:
  ```
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

## Algorithm

- Explicitly set to `HS256` (`ALGORITHM = "HS256"` in `auth/utils.py`)
- `decode_token` passes `algorithms=["HS256"]` and `options={"verify_signature": True}`
- The `"none"` algorithm is rejected — unsigned tokens will always fail verification

## Token Expiration

- Access tokens expire after **24 hours** (`ACCESS_TOKEN_EXPIRE_HOURS = 24`)
- No refresh token flow is implemented — users must re-login after expiry
- Expiration is enforced by `python-jose` during `decode_token`

## Token Audit — PASS

Audit conducted across all routers, services, auth, and main.py (16 files):

- Tokens are never logged
- Tokens are only returned in auth responses (`/api/auth/login`, `/api/auth/signup`)
- Error messages never echo back token values
- `hashed_password` is stripped from all user responses in `auth/dependencies.py`
- `SECRET_KEY` is never logged or included in error responses
- Rate limiter truncates token to 32 chars for keying — never logs the full token

## Environment Key Policy

- `.env.development` and `.env.production` **must use different `SECRET_KEY` values**
- Neither file should ever be committed to version control — add both to `.gitignore`
- Rotating the secret invalidates all active sessions — coordinate with a deploy
- Generate a fresh key per environment using the command above

## Tests

`backend/tests/test_jwt.py` covers:

- Happy path — valid token round-trips correctly
- Expiration — expired token returns `None` from `decode_token`
- Algorithm enforcement — HS512/HS384-signed tokens are rejected
- `"none"` algorithm — unsigned tokens are rejected
- Tampered token — modified signature or payload returns `None`
