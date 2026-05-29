import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.limiter import limiter
from app.auth.utils import decode_token
from app.routers.matchingRoutes import router as matchingRouter
from app.routers.userRoutes import router as userRouter
from app.routers.authRoutes import router as authRouter
from app.database import users_collection

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await users_collection.create_index("email", unique=True, sparse=True)
    yield

app = FastAPI(title="RoomMatch API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/health")
def health():
    return {"status": "ok"}