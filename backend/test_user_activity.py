"""
Tests for P3AD.3 — GET /api/admin/users/{user_id}/activity
"""

import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
import pytest_asyncio
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.auth.utils import create_access_token, hash_password

_STRONG_PASSWORD = "Tr0ub4dor&3"
_ADMIN_ID = 201
_NON_ADMIN_ID = 202
_TARGET_ID = 203
_OTHER_ID = 204

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
}

_NON_ADMIN_USER = {
    **_BASE_USER,
    "id": _NON_ADMIN_ID,
    "email": "nonadmin@test.com",
    "username": "normaluser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
}

_TARGET_USER = {
    **_BASE_USER,
    "id": _TARGET_ID,
    "email": "target@test.com",
    "username": "targetuser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
}

_OTHER_USER = {
    **_BASE_USER,
    "id": _OTHER_ID,
    "email": "other@test.com",
    "username": "otheruser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
}

_ADMIN_TOKEN = create_access_token({"sub": str(_ADMIN_ID)})
_NON_ADMIN_TOKEN = create_access_token({"sub": str(_NON_ADMIN_ID)})

_AUTH_ADMIN = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}
_AUTH_NON_ADMIN = {"Authorization": f"Bearer {_NON_ADMIN_TOKEN}"}


def _make_users_mock(users_by_id: dict):
    """Return an AsyncMock for users_collection that dispatches find_one by id filter."""
    mock = AsyncMock()

    async def _find_one(filter=None, **kwargs):
        if filter and "id" in filter:
            return dict(users_by_id.get(filter["id"])) if filter["id"] in users_by_id else None
        return None

    mock.find_one = AsyncMock(side_effect=_find_one)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": 1})
    return mock


def _make_to_list_cursor(docs: list):
    """Return an AsyncMock whose .find() returns an object with a .to_list() method."""
    cursor_mock = MagicMock()
    cursor_mock.to_list = AsyncMock(return_value=docs)
    return cursor_mock


def _make_collection_with_docs(docs_by_filter):
    """
    Return a mock collection whose find() dispatches to docs_by_filter.
    docs_by_filter is a callable: filter_dict -> list of docs.
    """
    mock = AsyncMock()

    def _find(filter=None, **kwargs):
        results = docs_by_filter(filter or {})
        return _make_to_list_cursor(results)

    mock.find = MagicMock(side_effect=_find)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    return mock


def _patches(users_mock, likes_mock, matches_mock, chat_mock):
    return [
        patch("app.routers.authRoutes.users_collection", users_mock),
        patch("app.auth.dependencies.users_collection", users_mock),
        patch("app.database.users_collection", users_mock),
        patch("app.routers.userRoutes.users_collection", users_mock),
        patch("app.routers.userRoutes.likes_collection", likes_mock),
        patch("app.routers.userRoutes.matches_collection", matches_mock),
        patch("app.routers.userRoutes.chat_collection", chat_mock),
    ]


def _empty_collection():
    return _make_collection_with_docs(lambda f: [])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_can_get_activity(monkeypatch):
    """Admin gets 200 with all three keys populated from real inserted documents."""
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    users_mock = _make_users_mock({
        _ADMIN_ID: _ADMIN_USER,
        _TARGET_ID: _TARGET_USER,
        _OTHER_ID: _OTHER_USER,
    })

    # One like sent from target to other
    like_doc = {"fromUser": _TARGET_ID, "toUser": _OTHER_ID, "createdAt": datetime.utcnow()}
    # One match involving target
    match_doc = {"user1_id": _TARGET_ID, "user2_id": _OTHER_ID, "confirmedAt": datetime.utcnow()}
    # One chat message from target to other
    chat_doc = {"fromUser": _TARGET_ID, "toUser": _OTHER_ID, "content": "hey", "createdAt": datetime.utcnow()}

    def _likes_filter(f):
        if f.get("fromUser") == _TARGET_ID:
            return [like_doc]
        return []

    def _matches_filter(f):
        or_clause = f.get("$or", [])
        for cond in or_clause:
            if cond.get("user1_id") == _TARGET_ID or cond.get("user2_id") == _TARGET_ID:
                return [match_doc]
        return []

    def _chat_filter(f):
        if f.get("fromUser") == _TARGET_ID:
            return [chat_doc]
        if f.get("toUser") == _TARGET_ID:
            return []
        return []

    likes_mock = _make_collection_with_docs(_likes_filter)
    matches_mock = _make_collection_with_docs(_matches_filter)
    chat_mock = _make_collection_with_docs(_chat_filter)

    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock, matches_mock, chat_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"/api/admin/users/{_TARGET_ID}/activity", headers=_AUTH_ADMIN)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "matches" in body
    assert "likes_sent" in body
    assert "chat_partners" in body
    assert isinstance(body["matches"], list)
    assert isinstance(body["likes_sent"], list)
    assert isinstance(body["chat_partners"], list)
    assert len(body["matches"]) == 1
    assert len(body["likes_sent"]) == 1
    assert len(body["chat_partners"]) == 1


@pytest.mark.asyncio
async def test_nonadmin_cannot_get_activity(monkeypatch):
    """Non-admin token receives 403."""
    monkeypatch.delenv("ADMIN_USER_IDS", raising=False)

    users_mock = _make_users_mock({_NON_ADMIN_ID: _NON_ADMIN_USER})
    likes_mock = _empty_collection()
    matches_mock = _empty_collection()
    chat_mock = _empty_collection()

    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock, matches_mock, chat_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"/api/admin/users/{_TARGET_ID}/activity", headers=_AUTH_NON_ADMIN)

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_activity_nonexistent_user(monkeypatch):
    """Admin requesting activity for a user_id that doesn't exist gets 404."""
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    users_mock = _make_users_mock({_ADMIN_ID: _ADMIN_USER})
    likes_mock = _empty_collection()
    matches_mock = _empty_collection()
    chat_mock = _empty_collection()

    _MISSING_ID = 9999

    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock, matches_mock, chat_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"/api/admin/users/{_MISSING_ID}/activity", headers=_AUTH_ADMIN)

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_activity_empty_user(monkeypatch):
    """User with no likes, matches, or chats returns all three keys as empty lists."""
    monkeypatch.setenv("ADMIN_USER_IDS", str(_ADMIN_ID))

    users_mock = _make_users_mock({
        _ADMIN_ID: _ADMIN_USER,
        _TARGET_ID: _TARGET_USER,
    })
    likes_mock = _empty_collection()
    matches_mock = _empty_collection()
    chat_mock = _empty_collection()

    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock, matches_mock, chat_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"/api/admin/users/{_TARGET_ID}/activity", headers=_AUTH_ADMIN)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["matches"] == []
    assert body["likes_sent"] == []
    assert body["chat_partners"] == []
