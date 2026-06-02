"""
Tests for P1.4 — forgot-password and reset-password endpoints.

POST /api/auth/forgot-password  → returns reset_token for known email, no token for unknown
POST /api/auth/reset-password   → validates token, resets password, invalidates on reuse
"""

import os
import hashlib
from datetime import datetime, timedelta, timezone
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch, call

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.auth.utils import hash_password, create_access_token

_STRONG_PASSWORD = "Tr0ub4dor&3"
_STRONG_PASSWORD_NEW = "N3wStr0ng!Pass"


def _make_user(user_id: int = 1, extra: dict = None) -> dict:
    base = {
        "id": user_id,
        "email": "resetuser@test.com",
        "hashed_password": hash_password(_STRONG_PASSWORD),
        "username": "resetuser",
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
        "gender": "male",
        "_id": "fake_object_id",
        "sleepScoreWD": {"value": 5.0, "isDealBreaker": False},
        "sleepScoreWE": {"value": 5.0, "isDealBreaker": False},
        "cleanlinessScore": {"value": 5.0, "isDealBreaker": False},
        "noiseToleranceScore": {"value": 5.0, "isDealBreaker": False},
        "guestsScore": {"value": 5.0, "isDealBreaker": False},
        "personalityScore": {"value": 5.0, "isDealBreaker": False},
        "smokingScore": {"value": 0.0, "isDealBreaker": False},
        "sharedSpaceScore": {"value": 5.0, "isDealBreaker": False},
        "communicationScore": {"value": 5.0, "isDealBreaker": False},
    }
    if extra:
        base.update(extra)
    return base


def _make_mock_collection(find_one_return=None):
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=find_one_return)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": 1})
    return mock


def _patches(mock_col):
    return [
        patch("app.routers.authRoutes.users_collection", mock_col),
        patch("app.auth.dependencies.users_collection", mock_col),
        patch("app.database.users_collection", mock_col),
    ]


@pytest_asyncio.fixture()
async def http_client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# forgot-password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_valid_email(http_client: AsyncClient):
    user = _make_user()
    mock_col = _make_mock_collection(find_one_return=dict(user))
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        response = await http_client.post(
            "/api/auth/forgot-password",
            json={"email": "resetuser@test.com"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "reset_token" in body, f"Expected reset_token in response: {body}"
    assert isinstance(body["reset_token"], str)
    assert len(body["reset_token"]) > 0


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_no_info_leak(http_client: AsyncClient):
    mock_col = _make_mock_collection(find_one_return=None)
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        response = await http_client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@test.com"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    # No token should be in the response for an unknown email
    assert "reset_token" not in body or body.get("reset_token") is None


# ---------------------------------------------------------------------------
# reset-password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_valid_token(http_client: AsyncClient):
    """Request a reset token, then use it to change the password."""
    user = _make_user()
    mock_col = _make_mock_collection(find_one_return=dict(user))

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        # Step 1: get a token
        forgot_resp = await http_client.post(
            "/api/auth/forgot-password",
            json={"email": "resetuser@test.com"},
        )
        assert forgot_resp.status_code == 200
        reset_token = forgot_resp.json()["reset_token"]

        # Build the user doc as it would look after the forgot-password update
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        user_with_token = {**user, "reset_token_hash": token_hash, "reset_token_expires": expires}
        mock_col.find_one = AsyncMock(return_value=dict(user_with_token))

        # Step 2: reset password
        reset_resp = await http_client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": _STRONG_PASSWORD_NEW},
        )
    assert reset_resp.status_code == 200, reset_resp.text
    assert reset_resp.json().get("message") == "Password reset successfully"


@pytest.mark.asyncio
async def test_reset_password_invalid_token(http_client: AsyncClient):
    mock_col = _make_mock_collection(find_one_return=None)
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        response = await http_client.post(
            "/api/auth/reset-password",
            json={"token": "totally-invalid-token", "new_password": _STRONG_PASSWORD_NEW},
        )
    assert response.status_code == 400, response.text
    assert "Invalid or expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_token_used_twice(http_client: AsyncClient):
    """After a successful reset, reusing the same token returns 400."""
    user = _make_user()
    mock_col = _make_mock_collection(find_one_return=dict(user))

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        forgot_resp = await http_client.post(
            "/api/auth/forgot-password",
            json={"email": "resetuser@test.com"},
        )
        assert forgot_resp.status_code == 200
        reset_token = forgot_resp.json()["reset_token"]

        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        user_with_token = {**user, "reset_token_hash": token_hash, "reset_token_expires": expires}

        # First use: token found
        mock_col.find_one = AsyncMock(return_value=dict(user_with_token))
        r1 = await http_client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": _STRONG_PASSWORD_NEW},
        )
        assert r1.status_code == 200, r1.text

        # Second use: token no longer in DB (consumed)
        mock_col.find_one = AsyncMock(return_value=None)
        r2 = await http_client.post(
            "/api/auth/reset-password",
            json={"token": reset_token, "new_password": _STRONG_PASSWORD_NEW},
        )
    assert r2.status_code == 400, r2.text
    assert "Invalid or expired" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_weak_password(http_client: AsyncClient):
    """Weak new password returns 422."""
    user = _make_user()
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    user_with_token = {**user, "reset_token_hash": token_hash, "reset_token_expires": expires}

    mock_col = _make_mock_collection(find_one_return=dict(user_with_token))
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        response = await http_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "password123"},
        )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_reset_password_expired_token(http_client: AsyncClient):
    """Token with a past expiry date returns 400."""
    user = _make_user()
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # Expiry in the past
    expired_at = datetime.now(timezone.utc) - timedelta(hours=2)
    user_with_expired = {**user, "reset_token_hash": token_hash, "reset_token_expires": expired_at}

    # The endpoint queries: reset_token_expires: {$gt: now}
    # With a mock, find_one always returns what we give it — but the actual
    # endpoint uses $gt which the mock won't filter. We simulate the expired case
    # by returning None (as the real DB would when the token is expired).
    mock_col = _make_mock_collection(find_one_return=None)
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        response = await http_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": _STRONG_PASSWORD_NEW},
        )
    assert response.status_code == 400, response.text
    assert "Invalid or expired" in response.json()["detail"]
