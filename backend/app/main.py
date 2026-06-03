import os
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
from starlette.responses import Response
from app.limiter import limiter
from app.auth.utils import decode_token
from app.routers.matchingRoutes import router as matchingRouter
from app.routers.userRoutes import router as userRouter
from app.routers.authRoutes import router as authRouter
from app.database import users_collection, counters_collection

_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
_ENV = os.getenv("ROOMMATCH_ENV", "production")


def _before_send(event, hint):
    if "exc_info" in hint:
        exc = hint["exc_info"][1]
        from fastapi import HTTPException
        if isinstance(exc, HTTPException) and exc.status_code in (401, 403, 404, 429):
            return None
    if "request" in event:
        event["request"].pop("cookies", None)
        headers = event.get("request", {}).get("headers", {})
        if "authorization" in headers:
            headers["authorization"] = "[Filtered]"
    return event


if _SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        environment=_ENV,
        traces_sample_rate=0.1 if _ENV == "production" else 0.0,
        send_default_pii=False,
        before_send=_before_send,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )


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


_UPLOAD_PATHS = {"/upload-photo"}  # substring match


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_BODY = 1 * 1024 * 1024  # 1 MB

    async def dispatch(self, request: Request, call_next):
        # Skip size check for photo upload endpoints
        if any(p in request.url.path for p in _UPLOAD_PATHS):
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY:
            return Response(
                content='{"detail": "Request body too large"}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await users_collection.create_index("email", unique=True, sparse=True)
    current_max = await users_collection.find_one(sort=[("id", -1)])
    max_id = current_max["id"] if current_max else 0
    await counters_collection.update_one(
        {"_id": "user_id"},
        {"$setOnInsert": {"seq": max_id}},
        upsert=True,
    )
    yield

app = FastAPI(title="RoomMatch API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(filter(None, [
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        os.getenv("ADMIN_FRONTEND_URL"),
    ])),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

class SecurityHeadersMiddleware:
    """Pure ASGI middleware that injects security headers at the http.response.start
    message level, before bytes are ever sent to the client.  This avoids the
    known Starlette issue where BaseHTTPMiddleware header mutations can be
    silently dropped on streaming responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                # unsafe-inline for style-src/script-src is temporary until inline styles/scripts are extracted
                # img-src includes cloudinary for profile photo uploads
                # connect-src includes production API host for cross-origin API calls
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; "
                    "img-src 'self' data: https://res.cloudinary.com; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "connect-src 'self' https://roommatematching.onrender.com"
                )
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        # loc is a tuple like ("body", "username") — expose field name only
        loc = error.get("loc", [])
        field = loc[-1] if loc else "unknown"
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(status_code=422, content={"detail": errors})


# Create uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded photos as static files at /uploads/filename.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(authRouter, prefix="/api")
app.include_router(matchingRouter, prefix="/api")
app.include_router(userRouter, prefix="/api")

@app.get("/")
def root():
    return {"status": "Matching Algorithm API running", "version": "0.2.0"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}

if os.getenv("ROOMMATCH_ENV", "production") != "production":
    @app.get("/debug/sentry-test")
    def trigger_sentry_error():
        raise RuntimeError("Sentry test error — intentional")
