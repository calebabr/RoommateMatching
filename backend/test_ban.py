"""
Tests for P2.1 — admin ban/unban endpoints and login ban enforcement.

Uses AsyncMock to avoid needing a real MongoDB; monkeypatch controls
ADMIN_USER_IDS so get_admin_user() sees the correct set at call time.
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
_ADMIN_ID = 99
_TARGET_ID = 55
_NON_ADMIN_ID = 42

_BASE_USER = {
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "gender": "male",
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

_ADMIN_USER = {
    **_BASE_USER,
    "id": _ADMIN_ID,
    "email": "admin@test.com",
    "username": "adminuser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
    "is_banned": False,
}

_TARGET_USER = {
    **_BASE_USER,
    "id": _TARGET_ID,
    "email": "target@test.com",
    "username": "targetuser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
    "is_banned": False,
}

_NON_ADMIN_USER = {
    **_BASE_USER,
    "id": _NON_ADMIN_ID,
    "email": "user@test.com",
    "username": "normaluser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
    "is_banned": False,
}

_ADMIN_TOKEN = create_access_token({"sub": str(_ADMIN_ID)})
_NON_ADMIN_TOKEN = create_access_token({"sub": str(_NON_ADMIN_ID)})

_AUTH_ADMIN = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}
_AUTH_NON_ADMIN = {"Authorization": f"Bearer {_NON_ADMIN_TOKEN}"}


def _make_mock_collection(user: dict):
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=dict(user))
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(matched_count=1, modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": 1})
    return mock


def _patches(users_mock):
    return [
        patch("app.routers.authRoutes.users_collection", users_mock),
        patch("app.auth.dependencies.users_collection", users_mock),
        patch("app.database.users_collection", users_mock),
        patch("app.routers.userRoutes.userProfileService.collection", users_mock),
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
            yield ac


# ---------------------------------------------------------------------------
# Ban tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_ban_user(admin_client, monkeypatch):
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    response = await ac.post(f"/api/admin/ban/{_TARGET_ID}", headers=_AUTH_ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "User banned"
    mock_col.update_one.assert_awaited_once_with(
        {"id": _TARGET_ID}, {"$set": {"is_banned": True}}
    )


@pytest.mark.asyncio
async def test_admin_unban_user(admin_client, monkeypatch):
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    response = await ac.post(f"/api/admin/unban/{_TARGET_ID}", headers=_AUTH_ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "User unbanned"
    mock_col.update_one.assert_awaited_once_with(
        {"id": _TARGET_ID}, {"$set": {"is_banned": False}}
    )


@pytest.mark.asyncio
async def test_nonadmin_cannot_ban(non_admin_client, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)

    response = await non_admin_client.post(
        f"/api/admin/ban/{_TARGET_ID}", headers=_AUTH_NON_ADMIN
    )

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_nonadmin_cannot_unban(non_admin_client, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)

    response = await non_admin_client.post(
        f"/api/admin/unban/{_TARGET_ID}", headers=_AUTH_NON_ADMIN
    )

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_ban_nonexistent_user(admin_client, monkeypatch):
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    # Simulate no document matched
    mock_col.update_one = AsyncMock(return_value=MagicMock(matched_count=0, modified_count=0))

    response = await ac.post(f"/api/admin/ban/99999", headers=_AUTH_ADMIN)

    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# Login ban enforcement tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_banned_user_cannot_login(monkeypatch):
    """Banning a user and then logging in should return 403."""
    banned_user = {**_TARGET_USER, "is_banned": True}
    mock_col = _make_mock_collection(banned_user)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/login",
                json={"email": _TARGET_USER["email"], "password": _STRONG_PASSWORD},
            )

    assert response.status_code == 403, response.text
    assert "banned" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unbanned_user_can_login(monkeypatch):
    """After unbanning, the user can log in successfully."""
    active_user = {**_TARGET_USER, "is_banned": False}
    mock_col = _make_mock_collection(active_user)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/login",
                json={"email": _TARGET_USER["email"], "password": _STRONG_PASSWORD},
            )

    assert response.status_code == 200, response.text
    assert "access_token" in response.json()
