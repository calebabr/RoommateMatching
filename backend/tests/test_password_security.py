"""
Password security tests for RoomMatch.

Groups:
  1. Unit tests — hash_password / verify_password / validate_password_strength
     (no HTTP, no MongoDB required)
  2. API integration tests — FastAPI TestClient with mocked MongoDB collections
     (ROOMMATCH_ENV=test is set before any app import)

The file is self-contained: it does NOT rely on any conftest.py and does NOT
touch the real MongoDB instance.
"""

# ---------------------------------------------------------------------------
# Environment must be set BEFORE importing anything from app.*
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-password-security-tests")

# ---------------------------------------------------------------------------
# Standard-library / third-party imports
# ---------------------------------------------------------------------------
import importlib
import pytest
import bcrypt
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# App imports (safe now that env vars are set)
# ---------------------------------------------------------------------------
from app.auth.utils import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
)
from fastapi.testclient import TestClient
from app.main import app


# ===========================================================================
# Section 1: Unit tests — no HTTP, no DB
# ===========================================================================


def test_hash_password_uses_bcrypt_12_rounds():
    """hash_password must embed bcrypt cost-factor 12 in the produced hash."""
    hashed = hash_password("somepass")
    assert hashed.startswith("$2b$12$"), (
        f"Expected hash to start with '$2b$12$', got prefix: {hashed[:10]!r}"
    )


def test_verify_password_correct():
    """verify_password returns True when the plain password matches the hash."""
    plain = "CorrectHorseBatteryStaple!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    """verify_password returns False for the wrong plain password."""
    plain = "CorrectHorseBatteryStaple!"
    hashed = hash_password(plain)
    assert verify_password("WrongPassword!", hashed) is False


def test_validate_rejects_too_short():
    """validate_password_strength raises ValueError mentioning 'at least' for a 3-char password."""
    with pytest.raises(ValueError, match=r"at least"):
        validate_password_strength("abc")


def test_validate_rejects_password123():
    """
    'password123' is a very common password — zxcvbn scores it < 2.
    validate_password_strength must raise ValueError.
    """
    with pytest.raises(ValueError):
        validate_password_strength("password123")


def test_validate_rejects_common_weak():
    """Several well-known weak passwords must each raise ValueError."""
    weak_passwords = ["12345678", "qwertyui"]
    for pw in weak_passwords:
        with pytest.raises(ValueError):
            validate_password_strength(pw)


# Rewrite test_validate_rejects_common_weak without nested with blocks
def test_validate_rejects_12345678():
    """'12345678' is a sequential number run — zxcvbn score < 2."""
    with pytest.raises(ValueError):
        validate_password_strength("12345678")


def test_validate_rejects_qwertyui():
    """'qwertyui' is a keyboard pattern — zxcvbn score < 2."""
    with pytest.raises(ValueError):
        validate_password_strength("qwertyui")


def test_validate_accepts_strong():
    """'Tr0ub4dor&3' is a well-known strong-password example — must NOT raise."""
    # Should complete without raising
    validate_password_strength("Tr0ub4dor&3")


def test_min_length_env_override():
    """
    When MIN_PASSWORD_LENGTH env var is raised to 12, a 10-character password
    that would otherwise pass length check must be rejected with 'at least'.
    The env var is restored after the test.
    """
    import app.auth.utils as auth_utils

    original_env = os.environ.get("MIN_PASSWORD_LENGTH")
    original_module_val = auth_utils.MIN_PASSWORD_LENGTH

    try:
        os.environ["MIN_PASSWORD_LENGTH"] = "12"
        # Patch the module-level constant so the running code sees the new value
        auth_utils.MIN_PASSWORD_LENGTH = 12

        # 10-char password: long enough under the default (8) but not under 12
        with pytest.raises(ValueError, match=r"at least"):
            auth_utils.validate_password_strength("G#8kLm!qR2")  # 10 chars
    finally:
        # Always restore
        auth_utils.MIN_PASSWORD_LENGTH = original_module_val
        if original_env is None:
            os.environ.pop("MIN_PASSWORD_LENGTH", None)
        else:
            os.environ["MIN_PASSWORD_LENGTH"] = original_env


# ===========================================================================
# Section 2: API integration tests — TestClient + mocked MongoDB
# ===========================================================================
#
# Strategy:
#   - Use FastAPI's synchronous TestClient (simpler than httpx.AsyncClient for
#     these tests since the mocking happens at the collection level).
#   - Patch the THREE locations that reference users_collection:
#       * app.routers.authRoutes.users_collection  (register / login / change-pw)
#       * app.auth.dependencies.users_collection   (get_current_user)
#       * app.database.users_collection            (lifespan create_index call)
#   - Each test builds a minimal AsyncMock tailored to its scenario.
# ---------------------------------------------------------------------------

_STRONG_PASSWORD = "Tr0ub4dor&3"
_STRONG_PASSWORD_NEW = "G#8kLm!qR2$v"


def _make_mock_collection():
    """Return an AsyncMock that satisfies the Motor collection interface."""
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=None)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    return mock


def _patch_all_collections(mock_col):
    """Return a context manager list that patches every import site at once."""
    return [
        patch("app.routers.authRoutes.users_collection", mock_col),
        patch("app.auth.dependencies.users_collection", mock_col),
        patch("app.database.users_collection", mock_col),
    ]


# ---------------------------------------------------------------------------
# Helper: enter a stack of context managers
# ---------------------------------------------------------------------------
from contextlib import ExitStack


def _apply_patches(patches):
    stack = ExitStack()
    for p in patches:
        stack.enter_context(p)
    return stack


# ---------------------------------------------------------------------------
# 2a. Register endpoint — password validation
# ---------------------------------------------------------------------------


def test_register_rejects_weak_password():
    """
    POST /api/auth/register with 'password123' must return 422 (weak password).
    DB should never be reached because validation fires first.
    """
    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(return_value=None)  # no duplicate email

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/register",
            json={
                "email": "weakpw@test.com",
                "password": "password123",
                "username": "weakuser",
            },
        )

    assert response.status_code == 422, (
        f"Expected 422 for weak password, got {response.status_code}: {response.text}"
    )


def test_register_rejects_short_password():
    """
    POST /api/auth/register with a 5-character password must return 422.
    """
    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(return_value=None)

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/register",
            json={
                "email": "shortpw@test.com",
                "password": "abc12",
                "username": "shortuser",
            },
        )

    assert response.status_code == 422, (
        f"Expected 422 for short password, got {response.status_code}: {response.text}"
    )


def test_register_accepts_strong_password():
    """
    POST /api/auth/register with a strong password must return 201.
    Response body must contain 'access_token' and 'user'.
    The 'user' dict must NOT contain 'hashed_password' or 'password'.
    """
    mock_col = _make_mock_collection()
    # No existing user (no duplicate email)
    mock_col.find_one = AsyncMock(return_value=None)
    # insert_one succeeds; returned doc has _id stripped by the route handler
    mock_col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/register",
            json={
                "email": "strongpw@test.com",
                "password": _STRONG_PASSWORD,
                "username": "stronguser",
            },
        )

    assert response.status_code == 201, (
        f"Expected 201 for strong password, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "access_token" in data, "Response must contain 'access_token'"
    assert "user" in data, "Response must contain 'user'"

    user = data["user"]
    assert "hashed_password" not in user, (
        "Response user dict must NOT expose 'hashed_password'"
    )
    assert "password" not in user, (
        "Response user dict must NOT expose 'password'"
    )


# ---------------------------------------------------------------------------
# 2b. Login endpoint — no password leakage
# ---------------------------------------------------------------------------


def test_login_does_not_return_hashed_password():
    """
    POST /api/auth/login must strip 'hashed_password' from the response even
    though the stored document contains it.
    """
    # Build a realistic stored user document including hashed_password
    stored_hash = hash_password(_STRONG_PASSWORD)
    stored_user = {
        "id": 42,
        "email": "logintest@test.com",
        "hashed_password": stored_hash,
        "username": "loginuser",
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
        "gender": "",
    }

    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(return_value=dict(stored_user))  # fresh copy

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/login",
            json={
                "email": "logintest@test.com",
                "password": _STRONG_PASSWORD,
            },
        )

    assert response.status_code == 200, (
        f"Expected 200 for valid login, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "hashed_password" not in body, (
        "Top-level response must not expose 'hashed_password'"
    )
    if "user" in body:
        assert "hashed_password" not in body["user"], (
            "Nested 'user' dict in login response must not expose 'hashed_password'"
        )


# ---------------------------------------------------------------------------
# 2c. change-password endpoint
# ---------------------------------------------------------------------------


def _make_stored_user(password: str, user_id: int = 1) -> dict:
    """Build a minimal user document with a bcrypt hash for the given password."""
    return {
        "id": user_id,
        "email": "chpwtest@test.com",
        "hashed_password": hash_password(password),
        "username": "chpwuser",
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
        "gender": "",
    }


def test_change_password_rejects_wrong_current():
    """
    POST /api/auth/change-password with the wrong current_password must return 401.
    """
    user_id = 1
    stored = _make_stored_user(_STRONG_PASSWORD, user_id=user_id)
    token = create_access_token({"sub": str(user_id)})

    mock_col = _make_mock_collection()
    # get_current_user (dependencies) calls find_one({"id": int(user_id)})
    # change_password route also calls find_one({"id": current_user["id"]})
    # Both return the same stored document (fresh copy each call via side_effect)
    mock_col.find_one = AsyncMock(side_effect=lambda *a, **kw: dict(stored))

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "totally-wrong-password",
                "new_password": _STRONG_PASSWORD_NEW,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401, (
        f"Expected 401 for wrong current_password, got {response.status_code}: {response.text}"
    )


def test_change_password_rejects_weak_new_password():
    """
    POST /api/auth/change-password with a weak new_password must return 422.
    The current_password is correct; only the new one is too weak.
    """
    user_id = 2
    stored = _make_stored_user(_STRONG_PASSWORD, user_id=user_id)
    token = create_access_token({"sub": str(user_id)})

    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(side_effect=lambda *a, **kw: dict(stored))

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": _STRONG_PASSWORD,
                "new_password": "password123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422, (
        f"Expected 422 for weak new_password, got {response.status_code}: {response.text}"
    )


def test_change_password_succeeds():
    """
    POST /api/auth/change-password with the correct current_password and a strong
    new_password must return 200 with {'message': 'Password updated successfully'}.
    """
    user_id = 3
    stored = _make_stored_user(_STRONG_PASSWORD, user_id=user_id)
    token = create_access_token({"sub": str(user_id)})

    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(side_effect=lambda *a, **kw: dict(stored))
    mock_col.update_one = AsyncMock(return_value=MagicMock(modified_count=1))

    with _apply_patches(_patch_all_collections(mock_col)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": _STRONG_PASSWORD,
                "new_password": _STRONG_PASSWORD_NEW,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, (
        f"Expected 200 for valid change-password, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("message") == "Password updated successfully", (
        f"Unexpected response body: {body}"
    )
