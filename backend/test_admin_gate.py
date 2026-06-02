"""
Tests for P1.2/P1.3 — admin gating on /admin/recompute and /uploadUsers.

Uses AsyncMock to avoid needing a real MongoDB; monkeypatch controls
ADMIN_USER_IDS so get_admin_user() sees the correct set at call time.
"""

import os
import io
import json

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
_NON_ADMIN_ID = 42

_ADMIN_USER = {
    "id": _ADMIN_ID,
    "email": "admin@test.com",
    "username": "adminuser",
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

_NON_ADMIN_USER = {**_ADMIN_USER, "id": _NON_ADMIN_ID, "email": "user@test.com", "username": "normaluser"}

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
            yield ac


# ---------------------------------------------------------------------------
# /admin/recompute
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recompute_non_admin_403(non_admin_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    response = await non_admin_client.post("/api/admin/recompute", headers=_AUTH_NON_ADMIN)
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_recompute_admin_200(admin_client, monkeypatch):
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    # Two minimal user dicts that satisfy UserInDB validation
    _minimal_user = lambda uid: {
        "id": uid, "email": f"u{uid}@test.com", "username": f"user{uid}",
        "matched": False, "matchCount": 0, "matchedWith": [], "bio": "",
        "photoUrl": "", "lifestyleTags": [], "gender": "male",
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
    two_users = [_minimal_user(1), _minimal_user(2)]

    import app.routers.userRoutes as _ur
    original_svc = _ur.userProfileService
    original_rec = _ur.recommendationService
    mock_svc = MagicMock()
    mock_svc.get_all_active_users = AsyncMock(return_value=two_users)
    mock_rec = MagicMock()
    mock_rec.recompute_all = AsyncMock(return_value=None)
    _ur.userProfileService = mock_svc
    _ur.recommendationService = mock_rec
    try:
        response = await ac.post("/api/admin/recompute", headers=_AUTH_ADMIN)
    finally:
        _ur.userProfileService = original_svc
        _ur.recommendationService = original_rec

    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# /uploadUsers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_users_non_admin_403(non_admin_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)
    file_content = json.dumps({"users": []}).encode()
    response = await non_admin_client.post(
        "/api/uploadUsers",
        headers=_AUTH_NON_ADMIN,
        files={"file": ("users.json", io.BytesIO(file_content), "application/json")},
    )
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_upload_users_admin_200(admin_client, monkeypatch):
    ac, mock_col = admin_client
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    file_content = json.dumps({"users": []}).encode()

    with patch("app.routers.matchingRoutes.userProfileService") as mock_svc, \
         patch("app.routers.matchingRoutes.recommendationService") as mock_rec:
        mock_svc.get_all_active_users = AsyncMock(return_value=[])
        mock_rec.recompute_all = AsyncMock(return_value=None)
        response = await ac.post(
            "/api/uploadUsers",
            headers=_AUTH_ADMIN,
            files={"file": ("users.json", io.BytesIO(file_content), "application/json")},
        )

    assert response.status_code == 200, response.text
