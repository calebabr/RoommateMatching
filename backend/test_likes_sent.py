"""
Tests for the GET /api/users/{user_id}/likes-sent endpoint (P1.5 dependency).

Uses AsyncMock collections to avoid a real MongoDB connection.

Scenarios:
  - A likes B → A's likes-sent contains B's id
  - B has not liked anyone → B's likes-sent is empty
  - Unauthenticated request → 401 or 403
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

_USER_A_ID = 101
_USER_B_ID = 102
_STRONG_PASSWORD = "Tr0ub4dor&3"

_BASE_USER = {
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

_USER_A = {**_BASE_USER, "id": _USER_A_ID, "email": "a@test.com", "username": "userA"}
_USER_B = {**_BASE_USER, "id": _USER_B_ID, "email": "b@test.com", "username": "userB"}

_TOKEN_A = create_access_token({"sub": str(_USER_A_ID)})
_TOKEN_B = create_access_token({"sub": str(_USER_B_ID)})

_AUTH_A = {"Authorization": f"Bearer {_TOKEN_A}"}
_AUTH_B = {"Authorization": f"Bearer {_TOKEN_B}"}


def _make_users_mock(user: dict):
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=dict(user))
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": 1})
    return mock


def _async_cursor(docs: list):
    """Return an async iterable that yields the given docs."""
    class _Cursor:
        def __aiter__(self):
            return self._gen()
        async def _gen(self):
            for d in docs:
                yield d
    return _Cursor()


def _make_likes_mock(likes_for_a: list, likes_for_b: list):
    """
    Build a mock likes collection where find() returns different results
    depending on the fromUser filter value.
    """
    mock = AsyncMock()

    def _find(filter=None, **kwargs):
        from_user = (filter or {}).get("fromUser")
        if from_user == _USER_A_ID:
            return _async_cursor(likes_for_a)
        if from_user == _USER_B_ID:
            return _async_cursor(likes_for_b)
        return _async_cursor([])

    mock.find = _find
    mock.find_one = AsyncMock(return_value=None)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    return mock


def _patches(users_mock, likes_mock):
    return [
        patch("app.routers.authRoutes.users_collection", users_mock),
        patch("app.auth.dependencies.users_collection", users_mock),
        patch("app.database.users_collection", users_mock),
        patch("app.services.likeService.likes_collection", likes_mock),
        patch("app.services.likeService.users_collection", users_mock),
        patch("app.routers.userRoutes.likeService.likes", likes_mock),
        patch("app.routers.userRoutes.likeService.users", users_mock),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client_a_likes_b():
    """Client authenticated as A; A has one like sent to B."""
    users_mock = _make_users_mock(_USER_A)
    likes_mock = _make_likes_mock(
        likes_for_a=[{"fromUser": _USER_A_ID, "toUser": _USER_B_ID}],
        likes_for_b=[],
    )
    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture()
async def client_b_no_likes():
    """Client authenticated as B; B has sent no likes."""
    users_mock = _make_users_mock(_USER_B)
    likes_mock = _make_likes_mock(likes_for_a=[], likes_for_b=[])
    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture()
async def client_unauthenticated():
    """Client with no auth token."""
    users_mock = _make_users_mock(_USER_A)
    likes_mock = _make_likes_mock(likes_for_a=[], likes_for_b=[])
    with ExitStack() as stack:
        for p in _patches(users_mock, likes_mock):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_likes_sent_contains_target(client_a_likes_b: AsyncClient):
    """A liked B, so A's likes-sent should include B's id."""
    resp = await client_a_likes_b.get(
        f"/api/users/{_USER_A_ID}/likes-sent", headers=_AUTH_A
    )
    assert resp.status_code == 200, resp.text
    sent = resp.json()
    assert _USER_B_ID in sent, f"Expected {_USER_B_ID} in likes-sent {sent}"


@pytest.mark.asyncio
async def test_likes_sent_empty_for_b(client_b_no_likes: AsyncClient):
    """B has not liked anyone; likes-sent should be empty."""
    resp = await client_b_no_likes.get(
        f"/api/users/{_USER_B_ID}/likes-sent", headers=_AUTH_B
    )
    assert resp.status_code == 200, resp.text
    sent = resp.json()
    assert sent == [], f"Expected empty likes-sent for B, got {sent}"


@pytest.mark.asyncio
async def test_likes_sent_unauthenticated(client_unauthenticated: AsyncClient):
    """No auth token should be rejected with 401 or 403."""
    resp = await client_unauthenticated.get(
        f"/api/users/{_USER_A_ID}/likes-sent"
    )
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}"
    )
