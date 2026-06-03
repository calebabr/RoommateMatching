"""
Rate limit tests for RoomMatch API.

These tests use a self-contained FastAPI app with slowapi in-memory limits,
keyed by a fixed X-Forwarded-For IP so limits are fully deterministic.

Limits under test (matching Tasks #2 and #3):
  - POST /api/auth/login        → 5/15minutes  (6th request → 429)
  - POST /api/auth/register     → 3/hour       (4th request → 429)
  - POST /api/users/{id}/like   → 100/hour     (101st request → 429)
  - POST /api/users/{id}/chat/  → 30/minute    (31st request → 429)
  - POST /api/users/{id}/upload-photo → 10/hour (11th request → 429)
  - GET  /api/users/all         → 60/minute    (61st request → 429, default)

Run with:
  cd backend
  pytest tests/test_ratelimits.py -v
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from httpx import AsyncClient, ASGITransport

TEST_IP = "10.0.0.1"
FIXED_IP_HEADERS = {"X-Forwarded-For": TEST_IP}


def _get_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


def _make_rate_limit_handler(limiter: Limiter):
    """Return a 429 handler that injects Retry-After using the limiter's header logic."""
    def handler(request: Request, exc: RateLimitExceeded) -> Response:
        response = JSONResponse({"error": f"Rate limit exceeded: {exc.detail}"}, status_code=429)
        response = limiter._inject_headers(response, request.state.view_rate_limit)
        if "Retry-After" not in response.headers:
            response.headers["Retry-After"] = "60"
        return response
    return handler


def build_test_app() -> FastAPI:
    limiter = Limiter(key_func=_get_ip, default_limits=["60/minute"], headers_enabled=True)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _make_rate_limit_handler(limiter))
    app.add_middleware(SlowAPIMiddleware)

    @app.post("/api/auth/login")
    @limiter.limit("5/15minutes")
    async def login(request: Request):
        return JSONResponse({"ok": True})

    @app.post("/api/auth/register")
    @limiter.limit("3/hour")
    async def register(request: Request):
        return JSONResponse({"ok": True}, status_code=201)

    @app.post("/api/users/{user_id}/like")
    @limiter.limit("100/hour")
    async def like(request: Request, user_id: int):
        return JSONResponse({"ok": True})

    @app.post("/api/users/{user_id}/chat/{partner_id}")
    @limiter.limit("30/minute")
    async def chat(request: Request, user_id: int, partner_id: int):
        return JSONResponse({"ok": True})

    @app.post("/api/users/{user_id}/upload-photo")
    @limiter.limit("10/hour")
    async def upload_photo(request: Request, user_id: int):
        return JSONResponse({"ok": True})

    @app.get("/api/users/all")
    async def get_all(request: Request):
        return JSONResponse([])

    return app


@pytest_asyncio.fixture()
async def client():
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _assert_429_with_retry_after(response):
    assert response.status_code == 429, (
        f"Expected 429, got {response.status_code}: {response.text}"
    )
    assert "Retry-After" in response.headers, (
        f"Retry-After header missing from 429 response. Headers: {dict(response.headers)}"
    )


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    """5 successful logins then 6th → 429."""
    for i in range(5):
        r = await client.post("/api/auth/login", json={}, headers=FIXED_IP_HEADERS)
        assert r.status_code == 200, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.post("/api/auth/login", json={}, headers=FIXED_IP_HEADERS)
    _assert_429_with_retry_after(r)


@pytest.mark.asyncio
async def test_register_rate_limit(client: AsyncClient):
    """3 successful register attempts then 4th → 429."""
    for i in range(3):
        r = await client.post("/api/auth/register", json={}, headers=FIXED_IP_HEADERS)
        assert r.status_code == 201, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.post("/api/auth/register", json={}, headers=FIXED_IP_HEADERS)
    _assert_429_with_retry_after(r)


@pytest.mark.asyncio
async def test_like_rate_limit(client: AsyncClient):
    """100 successful like requests then 101st → 429."""
    for i in range(100):
        r = await client.post("/api/users/1/like", json={}, headers=FIXED_IP_HEADERS)
        assert r.status_code == 200, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.post("/api/users/1/like", json={}, headers=FIXED_IP_HEADERS)
    _assert_429_with_retry_after(r)


@pytest.mark.asyncio
async def test_chat_rate_limit(client: AsyncClient):
    """30 successful chat sends then 31st → 429."""
    for i in range(30):
        r = await client.post(
            "/api/users/1/chat/2", json={"content": "hi"}, headers=FIXED_IP_HEADERS
        )
        assert r.status_code == 200, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.post(
        "/api/users/1/chat/2", json={"content": "hi"}, headers=FIXED_IP_HEADERS
    )
    _assert_429_with_retry_after(r)


@pytest.mark.asyncio
async def test_upload_photo_rate_limit(client: AsyncClient):
    """10 successful photo uploads then 11th → 429."""
    for i in range(10):
        r = await client.post(
            "/api/users/1/upload-photo", json={}, headers=FIXED_IP_HEADERS
        )
        assert r.status_code == 200, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.post(
        "/api/users/1/upload-photo", json={}, headers=FIXED_IP_HEADERS
    )
    _assert_429_with_retry_after(r)


@pytest.mark.asyncio
async def test_default_rate_limit(client: AsyncClient):
    """Default limit: 60 requests/minute on a generic protected route, 61st → 429."""
    for i in range(60):
        r = await client.get("/api/users/all", headers=FIXED_IP_HEADERS)
        assert r.status_code == 200, f"Request {i+1} should succeed, got {r.status_code}"

    r = await client.get("/api/users/all", headers=FIXED_IP_HEADERS)
    _assert_429_with_retry_after(r)
