"""
Tests for P2.2 — is_admin field in login/me responses and GET /api/admin/users.
"""

import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
import pytest_asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.auth.utils import create_access_token, hash_password

_STRONG_PASSWORD = "Tr0ub4dor&3"
_ADMIN_ID = 101
_NON_ADMIN_ID = 102

_ADMIN_USER = {
    "id": _ADMIN_ID,
    "email": "admin_resp@test.com",
    "username": "adminrespuser",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "gender": "male",
    "hashed_password": hash_password(_STRONG_PASSWORD),
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

_NON_ADMIN_USER = {
    **_ADMIN_USER,
    "id": _NON_ADMIN_ID,
    "email": "user_resp@test.com",
    "username": "normalrespuser",
}

_ADMIN_TOKEN = create_access_token({"sub": str(_ADMIN_ID)})
_NON_ADMIN_TOKEN = create_access_token({"sub": str(_NON_ADMIN_ID)})

_AUTH_ADMIN = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}
_AUTH_NON_ADMIN = {"Authorization": f"Bearer {_NON_ADMIN_TOKEN}"}


def _make_mock_collection(user: dict):
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=dict(user))
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": 1})
    return mock


def _patches(users_mock):
    return [
        patch("app.routers.authRoutes.users_collection", users_mock),
        patch("app.auth.dependencies.users_collection", users_mock),
        patch("app.database.users_collection", users_mock),
    ]


@pytest_asyncio.fixture()
async def admin_client():
    mock_col = _make_mock_collection(_ADMIN_USER)
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, mock_col


@pytest_asyncio.fixture()
async def non_admin_client():
    mock_col = _make_mock_collection(_NON_ADMIN_USER)
    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, mock_col


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_includes_is_admin_true(admin_client, monkeypatch):
    """Login as admin user — response user object must include is_admin: true."""
    ac, _ = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))
    response = await ac.post(
        "/api/auth/login",
        json={"email": _ADMIN_USER["email"], "password": _STRONG_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["is_admin"] is True


@pytest.mark.asyncio
async def test_login_includes_is_admin_false(non_admin_client, monkeypatch):
    """Login as non-admin user — response user object must include is_admin: false."""
    ac, _ = non_admin_client
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    response = await ac.post(
        "/api/auth/login",
        json={"email": _NON_ADMIN_USER["email"], "password": _STRONG_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["is_admin"] is False


@pytest.mark.asyncio
async def test_me_includes_is_admin_true(admin_client, monkeypatch):
    """GET /api/auth/me with admin token — response must include is_admin: true."""
    ac, _ = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))
    response = await ac.get("/api/auth/me", headers=_AUTH_ADMIN)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_admin_users_endpoint_returns_list(admin_client, monkeypatch):
    """Admin calling GET /api/admin/users — 200 with a list where each item has an id."""
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    # mock the cursor returned by userProfileService.collection.find
    user_doc = {k: v for k, v in _ADMIN_USER.items() if k not in ("hashed_password",)}

    async def _async_gen(*args, **kwargs):
        yield dict(user_doc)

    mock_find_cursor = MagicMock()
    mock_find_cursor.__aiter__ = lambda self: _async_gen()

    with patch("app.routers.userRoutes.userProfileService") as mock_svc:
        mock_svc.collection.find.return_value = mock_find_cursor
        response = await ac.get("/api/admin/users", headers=_AUTH_ADMIN)

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "id" in data[0]


@pytest.mark.asyncio
async def test_nonadmin_cannot_list_users(non_admin_client, monkeypatch):
    """Non-admin calling GET /api/admin/users — must receive 403."""
    ac, _ = non_admin_client
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    response = await ac.get("/api/admin/users", headers=_AUTH_NON_ADMIN)
    assert response.status_code == 403, response.text
