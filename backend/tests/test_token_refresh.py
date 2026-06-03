"""
Tests for P3A.1 — refresh token mechanism.

Covers: login/register return refresh_token, /refresh endpoint happy path,
token rotation, reuse prevention, logout invalidation, and downstream access
with a freshly-issued access token.

Uses Motor (real async MongoDB) pointed at roommatch_test, matching the
pattern from test_atomic_id.py so that async DB operations work correctly.
"""

import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient, ASGITransport

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"

# A password that passes zxcvbn strength check (score >= 2)
_STRONG_PASSWORD = "Tr0ub4dor&3"

_USER_COUNTER = 0  # incremented per test to avoid email collisions


def _unique_email() -> str:
    global _USER_COUNTER
    _USER_COUNTER += 1
    return f"refreshtest{_USER_COUNTER}@auburn.edu"


@pytest_asyncio.fixture(autouse=True)
async def clean_test_db():
    """Drop test collections before and after each test to ensure isolation."""
    motor_client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = motor_client[TEST_DB_NAME]
    await db["users"].drop()
    await db["counters"].drop()
    yield
    await db["users"].drop()
    await db["counters"].drop()
    motor_client.close()


@pytest_asyncio.fixture()
async def client():
    """Async HTTP client wired to the FastAPI app with an isolated Motor test DB."""
    import app.database
    import app.routers.authRoutes
    import app.auth.dependencies

    motor_client = AsyncIOMotorClient(TEST_MONGO_URL)
    db = motor_client[TEST_DB_NAME]

    users_col = db["users"]
    counters_col = db["counters"]

    # Redirect all DB references to the test database
    app.database.users_collection = users_col
    app.routers.authRoutes.users_collection = users_col
    app.routers.authRoutes.counters_collection = counters_col
    app.auth.dependencies.users_collection = users_col

    # Reset rate limiter buckets so register/login limits don't block tests
    from app.limiter import limiter
    storage = limiter._storage
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "_storage") and isinstance(storage._storage, dict):
        storage._storage.clear()

    from app.main import app as fastapi_app
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    motor_client.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _register_user(client: AsyncClient, email: str | None = None) -> dict:
    """Register a user and return the full response JSON."""
    if email is None:
        email = _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": _STRONG_PASSWORD,
            "username": email.split("@")[0],
            "gender": "male",
        },
    )
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return resp.json()


async def _login_user(client: AsyncClient, email: str) -> dict:
    """Login and return the full response JSON."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": _STRONG_PASSWORD},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_refresh_token(client: AsyncClient):
    """POST /api/auth/login response includes a non-empty refresh_token field."""
    email = _unique_email()
    await _register_user(client, email)
    data = await _login_user(client, email)

    assert "refresh_token" in data, "refresh_token key missing from login response"
    assert data["refresh_token"], "refresh_token must not be null or empty"
    assert isinstance(data["refresh_token"], str)


@pytest.mark.asyncio
async def test_register_returns_refresh_token(client: AsyncClient):
    """POST /api/auth/register response includes a non-empty refresh_token field."""
    data = await _register_user(client)

    assert "refresh_token" in data, "refresh_token key missing from register response"
    assert data["refresh_token"], "refresh_token must not be null or empty"
    assert isinstance(data["refresh_token"], str)


@pytest.mark.asyncio
async def test_refresh_with_valid_token_returns_new_tokens(client: AsyncClient):
    """POST /api/auth/refresh with a valid token returns 200 with access_token and refresh_token."""
    email = _unique_email()
    await _register_user(client, email)
    login_data = await _login_user(client, email)

    refresh_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )

    assert refresh_resp.status_code == 200, f"Expected 200, got: {refresh_resp.text}"
    result = refresh_resp.json()
    assert "access_token" in result, "access_token missing from refresh response"
    assert "refresh_token" in result, "refresh_token missing from refresh response"
    assert result["access_token"], "access_token must not be empty"
    assert result["refresh_token"], "refresh_token must not be empty"


@pytest.mark.asyncio
async def test_refresh_rotates_token(client: AsyncClient):
    """The refresh_token returned by /refresh differs from the one used in the request."""
    email = _unique_email()
    await _register_user(client, email)
    login_data = await _login_user(client, email)
    original_refresh_token = login_data["refresh_token"]

    refresh_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert refresh_resp.status_code == 200

    new_refresh_token = refresh_resp.json()["refresh_token"]
    assert new_refresh_token != original_refresh_token, (
        "Token rotation failed: new refresh_token is identical to the old one"
    )


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient):
    """POST /api/auth/refresh with a garbage token returns 401."""
    refresh_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "notavalidtoken"},
    )

    assert refresh_resp.status_code == 401, (
        f"Expected 401 for invalid token, got {refresh_resp.status_code}: {refresh_resp.text}"
    )


@pytest.mark.asyncio
async def test_refresh_with_used_token_returns_401(client: AsyncClient):
    """Using the same refresh token twice returns 401 on the second use (rotation invalidates old token)."""
    email = _unique_email()
    await _register_user(client, email)
    login_data = await _login_user(client, email)
    original_refresh_token = login_data["refresh_token"]

    # First use — should succeed
    first_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert first_resp.status_code == 200, f"First refresh failed: {first_resp.text}"

    # Second use of the same (now rotated-away) token — must be rejected
    second_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )
    assert second_resp.status_code == 401, (
        f"Expected 401 on reuse of rotated token, got {second_resp.status_code}: {second_resp.text}"
    )


@pytest.mark.asyncio
async def test_logout_clears_refresh_token(client: AsyncClient):
    """After logout, the original refresh token is rejected by /refresh."""
    email = _unique_email()
    await _register_user(client, email)
    login_data = await _login_user(client, email)
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # Logout with valid access token
    logout_resp = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"

    # Attempt to refresh using the now-invalidated refresh token
    refresh_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401, (
        f"Expected 401 after logout, got {refresh_resp.status_code}: {refresh_resp.text}"
    )


@pytest.mark.asyncio
async def test_new_access_token_from_refresh_is_valid(client: AsyncClient):
    """The access_token returned by /refresh grants access to GET /api/auth/me."""
    email = _unique_email()
    await _register_user(client, email)
    login_data = await _login_user(client, email)

    refresh_resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    new_access_token = refresh_resp.json()["access_token"]

    me_resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert me_resp.status_code == 200, (
        f"Expected 200 from /me with refreshed access token, got {me_resp.status_code}: {me_resp.text}"
    )
    assert me_resp.json()["email"] == email
