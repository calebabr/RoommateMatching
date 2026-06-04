"""
Tests for P2.27 — Age verification at registration and submit-age endpoint.

Covers:
  1. Register with valid DOB (18+) — succeeds
  2. Register with DOB under 18 — rejected with 400
  3. Register without DOB — succeeds (DOB optional)
  4. submit-age with valid adult DOB — {"status": "ok"}, dateOfBirth stored
  5. submit-age with underage DOB — {"status": "banned"}, is_banned=True
  6. submit-age unauthenticated — 401
  7. submit-age wrong user (ownership) — 403
  8. submit-age invalid date format — 400
  9. Banned user cannot login after submit-age bans them — 403
"""

import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch, call
from httpx import AsyncClient, ASGITransport
from app.auth.utils import create_access_token, hash_password

# ---------------------------------------------------------------------------
# Shared test fixtures / helpers
# ---------------------------------------------------------------------------

_STRONG_PASSWORD = "Tr0ub4dor&3"
_USER_ID = 7
_OTHER_USER_ID = 8

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

_USER_DOC = {
    **_BASE_USER,
    "id": _USER_ID,
    "email": "agetest@auburn.edu",
    "username": "agetest",
    "hashed_password": hash_password(_STRONG_PASSWORD),
    "is_banned": False,
}

_OTHER_USER_DOC = {
    **_BASE_USER,
    "id": _OTHER_USER_ID,
    "email": "other@auburn.edu",
    "username": "otheruser",
    "hashed_password": hash_password(_STRONG_PASSWORD),
    "is_banned": False,
}

_USER_TOKEN = create_access_token({"sub": str(_USER_ID)})
_OTHER_USER_TOKEN = create_access_token({"sub": str(_OTHER_USER_ID)})

_AUTH_USER = {"Authorization": f"Bearer {_USER_TOKEN}"}
_AUTH_OTHER = {"Authorization": f"Bearer {_OTHER_USER_TOKEN}"}


def _make_mock_collection(user: dict):
    """Return an AsyncMock collection that looks up by id."""
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=dict(user))
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(matched_count=1, modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    mock.find_one_and_update = AsyncMock(return_value={"seq": _USER_ID})
    return mock


def _patches(users_mock):
    """Return the list of patches needed to route all DB calls to users_mock."""
    return [
        patch("app.routers.authRoutes.users_collection", users_mock),
        patch("app.auth.dependencies.users_collection", users_mock),
        patch("app.database.users_collection", users_mock),
        patch("app.routers.userRoutes.users_collection", users_mock),
        patch("app.routers.userRoutes.userProfileService.collection", users_mock),
    ]


# ---------------------------------------------------------------------------
# Test: Registration with dateOfBirth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_with_adult_dob_succeeds():
    """Test 1: Register with a valid 18+ DOB — should return 201."""
    mock_col = _make_mock_collection({})
    # No existing user — find_one returns None so no duplicate
    mock_col.find_one = AsyncMock(return_value=None)
    mock_col.find_one_and_update = AsyncMock(return_value={"seq": 1})

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        # Also patch counters_collection used inside register
        stack.enter_context(patch("app.routers.authRoutes.counters_collection", mock_col))
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/register",
                json={
                    "email": "adult@auburn.edu",
                    "password": _STRONG_PASSWORD,
                    "username": "adultuser",
                    "dateOfBirth": "1990-06-15",  # clearly 18+
                },
            )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_register_with_underage_dob_rejected():
    """Test 2: Register with a DOB under 18 — should return 400."""
    from datetime import date
    # A DOB that makes the user 16 years old
    dob = date(date.today().year - 16, date.today().month, date.today().day).isoformat()

    mock_col = _make_mock_collection({})
    mock_col.find_one = AsyncMock(return_value=None)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        stack.enter_context(patch("app.routers.authRoutes.counters_collection", mock_col))
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/register",
                json={
                    "email": "kid@auburn.edu",
                    "password": _STRONG_PASSWORD,
                    "username": "younguser",
                    "dateOfBirth": dob,
                },
            )

    assert response.status_code == 400, response.text
    assert "18" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_without_dob_succeeds():
    """Test 3: Register without dateOfBirth — DOB is optional, should return 201."""
    mock_col = _make_mock_collection({})
    mock_col.find_one = AsyncMock(return_value=None)
    mock_col.find_one_and_update = AsyncMock(return_value={"seq": 2})

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        stack.enter_context(patch("app.routers.authRoutes.counters_collection", mock_col))
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/register",
                json={
                    "email": "nodob@auburn.edu",
                    "password": _STRONG_PASSWORD,
                    "username": "nodob",
                    # No dateOfBirth field
                },
            )

    assert response.status_code == 201, response.text
    assert "access_token" in response.json()


# ---------------------------------------------------------------------------
# Test: submit-age endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_age_adult_returns_ok():
    """Test 4: submit-age with a valid adult DOB — returns {"status": "ok"}, saves dateOfBirth."""
    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": "1990-01-01"},
                headers=_AUTH_USER,
            )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ok"

    # Verify update_one was called to save dateOfBirth
    mock_col.update_one.assert_awaited_once_with(
        {"id": _USER_ID},
        {"$set": {"dateOfBirth": "1990-01-01"}},
    )


@pytest.mark.asyncio
async def test_submit_age_underage_bans_user():
    """Test 5: submit-age with underage DOB — returns {"status": "banned"}, sets is_banned=True."""
    from datetime import date
    dob = date(date.today().year - 15, date.today().month, date.today().day).isoformat()

    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": dob},
                headers=_AUTH_USER,
            )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "banned"
    assert "banned" in data["message"].lower()

    # Verify update_one was called with is_banned=True
    mock_col.update_one.assert_awaited_once_with(
        {"id": _USER_ID},
        {"$set": {"is_banned": True, "ban_reason": "Age verification failed: user is under 18"}},
    )


@pytest.mark.asyncio
async def test_submit_age_unauthenticated_returns_401():
    """Test 6: submit-age without Authorization header — returns 401."""
    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": "1990-01-01"},
                # No Authorization header
            )

    assert response.status_code in (401, 403), response.text


@pytest.mark.asyncio
async def test_submit_age_wrong_user_returns_403():
    """Test 7: submit-age where authenticated user differs from path user_id — returns 403."""
    # _OTHER_USER_TOKEN authenticates as _OTHER_USER_ID
    # but we POST to _USER_ID's endpoint — ownership check should fail

    async def _side_effect_find_one(filter, **kwargs):
        uid = filter.get("id")
        if uid == _OTHER_USER_ID:
            return dict(_OTHER_USER_DOC)
        return dict(_USER_DOC)

    mock_col = _make_mock_collection(_OTHER_USER_DOC)
    mock_col.find_one = AsyncMock(side_effect=_side_effect_find_one)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",  # targeting _USER_ID
                json={"dateOfBirth": "1990-01-01"},
                headers=_AUTH_OTHER,  # authenticated as _OTHER_USER_ID
            )

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_submit_age_invalid_date_format_returns_400():
    """Test 8: submit-age with malformed date string — returns 400."""
    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": "not-a-date"},
                headers=_AUTH_USER,
            )

    assert response.status_code == 400, response.text
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_age_invalid_date_wrong_format_returns_400():
    """Test 8 (variant): submit-age with MM/DD/YYYY format instead of YYYY-MM-DD — returns 400."""
    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": "06/15/1990"},
                headers=_AUTH_USER,
            )

    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_banned_user_cannot_login_after_submit_age():
    """Test 9: After submit-age bans a user, login returns 403."""
    # Simulate a user that has already been banned (is_banned=True)
    banned_doc = {**_USER_DOC, "is_banned": True}
    mock_col = _make_mock_collection(banned_doc)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/login",
                json={"email": _USER_DOC["email"], "password": _STRONG_PASSWORD},
            )

    assert response.status_code == 403, response.text
    assert "banned" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_age_exactly_18_is_ok():
    """User turning exactly 18 today should pass age verification."""
    from datetime import date
    # Born exactly 18 years ago today
    today = date.today()
    dob = date(today.year - 18, today.month, today.day).isoformat()

    mock_col = _make_mock_collection(_USER_DOC)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/users/{_USER_ID}/submit-age",
                json={"dateOfBirth": dob},
                headers=_AUTH_USER,
            )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_invalid_dob_format_returns_400():
    """Register with a malformed dateOfBirth string returns 400."""
    mock_col = _make_mock_collection({})
    mock_col.find_one = AsyncMock(return_value=None)

    with ExitStack() as stack:
        for p in _patches(mock_col):
            stack.enter_context(p)
        stack.enter_context(patch("app.routers.authRoutes.counters_collection", mock_col))
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/auth/register",
                json={
                    "email": "baddob@auburn.edu",
                    "password": _STRONG_PASSWORD,
                    "username": "baddob",
                    "dateOfBirth": "15-06-1990",  # wrong format
                },
            )

    assert response.status_code == 400, response.text
    assert "invalid" in response.json()["detail"].lower()
