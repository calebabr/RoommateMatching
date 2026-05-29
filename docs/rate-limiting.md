# Rate Limiting

RoomMatch uses [slowapi](https://github.com/laurents/slowapi) — a FastAPI-compatible rate limiting library — to protect endpoints from abuse. In production, rate limit counters are stored in [Upstash Redis](https://upstash.com/) (a serverless Redis service with a free tier). Without Redis credentials, the app automatically falls back to an in-memory store suitable for local development.

---

## Environment Variables

| Variable | Required in prod | Description |
|---|---|---|
| `UPSTASH_REDIS_URL` | Yes | Standard `redis://` connection URL for your Upstash database — used by slowapi/limits for counter storage |
| `UPSTASH_REDIS_REST_URL` | Optional | Upstash REST API endpoint (future use / monitoring) |
| `UPSTASH_REDIS_REST_TOKEN` | Optional | Upstash REST API read/write token |
| `SENTRY_DSN` | Yes (prod) | DSN from your Sentry project — rate-limit hits are logged as events here |

> **Note:** slowapi uses the standard `redis://` protocol under the hood, not Upstash's HTTP REST API. Set `UPSTASH_REDIS_URL` to the `redis://` connection string shown in the Upstash console under **Connect** → **Redis URL**.

### Setting env vars

**PowerShell (development):**
```powershell
$env:UPSTASH_REDIS_URL   = "redis://default:your-token@your-db.upstash.io:6379"
$env:SENTRY_DSN          = "https://key@sentry.io/project-id"
```

**Bash/macOS/Linux (development):**
```bash
export UPSTASH_REDIS_URL="redis://default:your-token@your-db.upstash.io:6379"
export SENTRY_DSN="https://key@sentry.io/project-id"
```

Never commit these values to source control. In production, set them as platform secrets or in a `.env` file excluded from git.

---

## Rate Limit Table

| Route | Method | Limit | Key |
|---|---|---|---|
| `POST /api/auth/register` | Public | 3 / hour | IP address or Bearer token prefix |
| `POST /api/auth/login` | Public | 5 / 15 minutes | IP address or Bearer token prefix |
| `POST /api/users/{id}/like` | Authenticated | 100 / hour | Bearer token prefix |
| `POST /api/users/{id}/chat/{partner_id}` | Authenticated | 30 / minute | Bearer token prefix |
| `POST /api/users/{id}/upload-photo` | Authenticated | 10 / hour | Bearer token prefix |
| All other `/api/users/*` and `/api/admin/*` routes | Authenticated | 60 / minute | Bearer token prefix |

### How keys are assigned

The key function (`_get_user_or_ip` in `backend/app/limiter.py`) checks for a `Bearer` token in the `Authorization` header:

- **If a token is present:** uses the first 32 characters of the token as the key. This scopes the limit to the individual user/session even on shared networks (e.g., dorm Wi-Fi).
- **If no token is present:** falls back to the client's IP address (appropriate for public endpoints like register and login).

---

## Redis / Upstash Setup

Upstash provides a free-tier serverless Redis that requires no running server. Rate limit counters stored there are shared across all backend instances.

### Provisioning a free Upstash database

1. Create a free account at [upstash.com](https://upstash.com/).
2. Go to **Redis** → **Create database**.
3. Name it `roommatch-ratelimit`, choose the region closest to your deployment.
4. In the database dashboard, go to **Connect** and copy the **Redis URL** (format: `redis://default:<token>@<host>:6379`).
5. Set it as `UPSTASH_REDIS_URL` (see above).

### How it's wired in

`backend/app/limiter.py` builds the storage URI at import time:

```python
def _build_storage_uri() -> str:
    url = os.getenv("UPSTASH_REDIS_REST_URL", "")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    if url and token:
        redis_url = os.getenv("UPSTASH_REDIS_URL", "")
        if redis_url:
            return redis_url
    return "memory://"  # local dev fallback
```

If `UPSTASH_REDIS_URL` is not set, the limiter uses `memory://` — counters are per-process and reset on restart. This is fine for development but not for multi-instance production deployments.

`backend/app/main.py` wires the limiter into FastAPI with a custom Sentry-aware 429 handler:

```python
from app.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=_SENTRY_DSN, traces_sample_rate=0.0)

def _user_id_from_request(request: Request):
    """Extract integer user ID from Bearer token without hitting the DB."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload and "sub" in payload:
            try:
                return int(payload["sub"])
            except (ValueError, TypeError):
                pass
    return None

async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    if _SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.capture_message(
            f"Rate limit exceeded: {request.url.path}",
            level="warning",
            extras={
                "route": request.url.path,
                "ip": request.client.host if request.client else None,
                "user_id": _user_id_from_request(request),
            },
        )
    return JSONResponse(
        status_code=429,
        content={"error": "Too Many Requests", "detail": str(exc)},
        headers={"Retry-After": "60"},
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
```

`traces_sample_rate=0.0` disables performance tracing — only error/warning events are sent to Sentry. Sentry is initialized only when `SENTRY_DSN` is set, so local dev has zero Sentry overhead.

Routes apply limits with the `@limiter.limit(...)` decorator:

```python
@router.post("/register")
@limiter.limit("3/hour")
async def register(request: Request, body: RegisterRequest):
    ...

@router.post("/login")
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginRequest):
    ...
```

Note that `request: Request` must be the first parameter in any rate-limited handler — slowapi requires it to extract the key.

---

## Testing Rate Limits Locally

Start the backend (`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`), then use curl to trigger 429 responses. Because the default limits use per-hour or per-15-minute windows, it is easiest to test by hitting the limit quickly with the same IP.

### Trigger a 429 on `/api/auth/register` (limit: 3/hour)

```bash
for i in $(seq 1 4); do
  curl -s -o /dev/null -w "Attempt $i: %{http_code}\n" \
    -X POST http://localhost:8000/api/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"test${i}@auburn.edu\",\"password\":\"pass1234\",\"username\":\"tester${i}\"}"
done
```

Expected output: three `201`/`409` responses, then one `429`.

### Trigger a 429 on `/api/auth/login` (limit: 5/15minutes)

```bash
for i in $(seq 1 6); do
  curl -s -o /dev/null -w "Attempt $i: %{http_code}\n" \
    -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"you@auburn.edu","password":"wrongpass"}'
done
```

Expected output: five `401` responses, then one `429`.

### Inspect the 429 response body

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@auburn.edu","password":"wrongpass"}'
```

After the limit is exhausted, the response includes:

```json
{"error": "Too Many Requests", "detail": "5 per 15 minute"}
```

The response always includes `Retry-After: 60`.

### PowerShell equivalent

```powershell
1..4 | ForEach-Object {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/api/auth/register" `
        -Method POST -ContentType "application/json" `
        -Body "{`"email`":`"test$_@auburn.edu`",`"password`":`"pass1234`",`"username`":`"tester$_`"}" `
        -SkipHttpErrorCheck
    Write-Host "Attempt ${_}: $($r.StatusCode)"
}
```

---

## Monitoring with Sentry

When `SENTRY_DSN` is set, each 429 response is captured via `sentry_sdk.capture_message` in `main.py`'s `_rate_limit_handler`. Events appear in Sentry with:

| Field | Value |
|---|---|
| Message | `Rate limit exceeded: /api/auth/login` (route path) |
| Level | `warning` |
| Extra: `route` | Full request path (e.g. `/api/users/42/like`) |
| Extra: `ip` | Client IP address from `request.client.host` |
| Extra: `user_id` | Integer user ID decoded from the Bearer JWT `sub` claim via `decode_token` — no DB call. `null` for unauthenticated requests or invalid tokens. |

### What to look for in Sentry

| Pattern | Possible cause | Action |
|---|---|---|
| High-frequency 429s on `POST /api/auth/login` from one IP | Credential stuffing / brute-force | Block the IP at the infrastructure level; review MongoDB for the targeted account |
| High-frequency 429s on `POST /api/auth/register` from one IP | Account farming bot | Block IP; consider CAPTCHA |
| 429s from many distinct IPs in a short window | Distributed attack | Review Upstash Redis metrics; consider tightening limits or adding IP allowlisting |

### Sentry alert setup (recommended)

1. In your Sentry project, go to **Alerts** → **Create Alert Rule**.
2. Set condition: **Number of events > 10** in **1 minute**.
3. Add filter: `level = warning`.
4. Set action: notify via email or Slack.

This surfaces active abuse without noise from normal isolated 429s.
