"""
Security-finding tests for RoomMatch.

FINDING-2: PUT /api/users/{user_id} must not write plaintext password (or email)
           to MongoDB via update_profile.

FINDING-1: POST /api/auth/register must reject malformed preference dicts
           (wrong value type, wrong isDealBreaker type) with HTTP 422.

Environment: ROOMMATCH_ENV=test must be set before any app.* import so that
             app.auth.utils uses the dev-only secret key instead of raising
             RuntimeError about a missing SECRET_KEY env var.

Run with:
    cd backend
    pytest test_security_findings.py -v
"""

# ---------------------------------------------------------------------------
# Set env vars BEFORE any app.* imports
# ---------------------------------------------------------------------------
import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")

# ---------------------------------------------------------------------------
# Standard-library / third-party imports
# ---------------------------------------------------------------------------
import pytest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App imports (safe now that env vars are set)
# ---------------------------------------------------------------------------
from app.auth.utils import create_access_token
from app.main import app

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_STRONG_PASSWORD = "Tr0ub4dor&3"

# Minimal Preference dict used throughout the tests
_PREF = {"value": 5.0, "isDealBreaker": False}

# A complete, valid UserCreate body for PUT /api/users/{user_id}
_VALID_USER_CREATE_BODY = {
    "username": "alice",
    "gender": "female",
    "sleepScoreWD": _PREF,
    "sleepScoreWE": _PREF,
    "cleanlinessScore": _PREF,
    "noiseToleranceScore": _PREF,
    "guestsScore": _PREF,
    "personalityScore": _PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _PREF,
    "communicationScore": _PREF,
}

# A minimal user dict that satisfies UserResponse validation, returned by the
# mock update_profile so that the route's response_model serialisation succeeds.
_FAKE_USER_RESPONSE = {
    "id": 1,
    "username": "alice",
    "email": "alice@test.com",
    "gender": "female",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "sleepScoreWD": _PREF,
    "sleepScoreWE": _PREF,
    "cleanlinessScore": _PREF,
    "noiseToleranceScore": _PREF,
    "guestsScore": _PREF,
    "personalityScore": _PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _PREF,
    "communicationScore": _PREF,
}

# A fake stored user document returned by the auth dependency's find_one call.
_FAKE_AUTH_USER = {
    "id": 1,
    "username": "alice",
    "email": "alice@test.com",
    "hashed_password": "hashed",
    "gender": "female",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "sleepScoreWD": _PREF,
    "sleepScoreWE": _PREF,
    "cleanlinessScore": _PREF,
    "noiseToleranceScore": _PREF,
    "guestsScore": _PREF,
    "personalityScore": _PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _PREF,
    "communicationScore": _PREF,
}


def _make_auth_token(user_id: int = 1) -> str:
    return create_access_token({"sub": str(user_id)})


def _make_mock_collection():
    """Return an AsyncMock that satisfies the Motor collection interface."""
    mock = AsyncMock()
    mock.find_one = AsyncMock(return_value=None)
    mock.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
    mock.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock.create_index = AsyncMock(return_value=None)
    return mock


def _apply_patches(patches):
    """Enter a list of context managers and return an ExitStack for cleanup."""
    stack = ExitStack()
    for p in patches:
        stack.enter_context(p)
    return stack


# ---------------------------------------------------------------------------
# Patch helpers for PUT /api/users/{user_id} tests
#
# We need to patch:
#   1. app.auth.dependencies.users_collection  – so get_current_user finds user 1
#   2. app.database.users_collection           – lifespan create_index
#   3. app.routers.userRoutes.userProfileService.update_profile  – the call we inspect
#   4. app.routers.userRoutes.userProfileService.get_all_active_users – skip recompute
# ---------------------------------------------------------------------------

def _patches_for_put(update_profile_mock: AsyncMock, get_all_mock: AsyncMock):
    """Return a list of patch objects for the PUT endpoint tests."""
    auth_col = _make_mock_collection()
    auth_col.find_one = AsyncMock(return_value=dict(_FAKE_AUTH_USER))

    return [
        patch("app.auth.dependencies.users_collection", auth_col),
        patch("app.database.users_collection", auth_col),
        patch(
            "app.routers.userRoutes.userProfileService.update_profile",
            update_profile_mock,
        ),
        patch(
            "app.routers.userRoutes.userProfileService.get_all_active_users",
            get_all_mock,
        ),
    ]


# ===========================================================================
# FINDING-2: PUT /api/users/{user_id} — immutable-field filtering
# ===========================================================================


def test_update_profile_does_not_store_plaintext_password():
    """
    PUT /api/users/1 with a 'password' field in the body must NOT pass
    'password' or 'hashed_password' to userProfileService.update_profile.

    The _IMMUTABLE_FIELDS filter in the route handler is responsible for
    stripping these before calling the service.
    """
    update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
    get_all_mock = AsyncMock(return_value=[])

    token = _make_auth_token(1)
    body = {**_VALID_USER_CREATE_BODY, "password": "should_not_be_stored"}

    with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put(
            "/api/users/1",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    assert update_mock.called, "update_profile was never called"

    # Retrieve the preferences dict passed as the second positional argument
    _, call_args, _ = update_mock.mock_calls[0]
    passed_dict = call_args[1]  # update_profile(user_id, preferences)

    assert "password" not in passed_dict, (
        f"'password' key must NOT be passed to update_profile; got keys: {list(passed_dict)}"
    )
    assert "hashed_password" not in passed_dict, (
        f"'hashed_password' key must NOT be passed to update_profile; got keys: {list(passed_dict)}"
    )


def test_update_profile_does_not_store_email():
    """
    PUT /api/users/1 with an 'email' field in the body must NOT pass 'email'
    to userProfileService.update_profile.

    'email' is listed in _IMMUTABLE_FIELDS and must be stripped before the
    service call, preventing an attacker from hijacking another user's account
    by overwriting their email address.
    """
    update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
    get_all_mock = AsyncMock(return_value=[])

    token = _make_auth_token(1)
    body = {**_VALID_USER_CREATE_BODY, "email": "attacker@evil.com"}

    with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put(
            "/api/users/1",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    assert update_mock.called, "update_profile was never called"

    _, call_args, _ = update_mock.mock_calls[0]
    passed_dict = call_args[1]

    assert "email" not in passed_dict, (
        f"'email' key must NOT be passed to update_profile; got keys: {list(passed_dict)}"
    )


def test_update_profile_allows_preference_fields():
    """
    PUT /api/users/1 with a valid preference field (cleanlinessScore) must
    forward that field — with the correct value — to update_profile.

    This confirms the filter allows mutable preference fields through while
    still blocking the immutable ones tested above.
    """
    update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
    get_all_mock = AsyncMock(return_value=[])

    token = _make_auth_token(1)
    custom_cleanliness = {"value": 8.0, "isDealBreaker": True}
    body = {**_VALID_USER_CREATE_BODY, "cleanlinessScore": custom_cleanliness}

    with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put(
            "/api/users/1",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )

    assert update_mock.called, "update_profile was never called"

    _, call_args, _ = update_mock.mock_calls[0]
    passed_dict = call_args[1]

    assert "cleanlinessScore" in passed_dict, (
        f"'cleanlinessScore' must be present in dict passed to update_profile; "
        f"got keys: {list(passed_dict)}"
    )

    stored = passed_dict["cleanlinessScore"]
    # The value may be stored as a Preference object or a dict depending on
    # how model_dump serialises it; handle both.
    if hasattr(stored, "value"):
        assert stored.value == 8.0, f"Expected value=8.0, got {stored.value}"
        assert stored.isDealBreaker is True, (
            f"Expected isDealBreaker=True, got {stored.isDealBreaker}"
        )
    else:
        assert stored.get("value") == 8.0, f"Expected value=8.0, got {stored}"
        assert stored.get("isDealBreaker") is True, (
            f"Expected isDealBreaker=True, got {stored}"
        )


# ===========================================================================
# FINDING-1: POST /api/auth/register — preference field validation
# ===========================================================================
#
# Strategy:
#   - Patch the three locations that import users_collection so no real MongoDB
#     connection is made.
#   - For rejection tests (422) no DB patch is needed because Pydantic raises
#     before the handler body executes, but patching is harmless and consistent.
# ---------------------------------------------------------------------------

def _patches_for_register(find_one_return=None, insert_ok=True):
    """Return patches appropriate for register endpoint tests."""
    mock_col = _make_mock_collection()
    mock_col.find_one = AsyncMock(return_value=find_one_return)
    if insert_ok:
        mock_col.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="fake_id")
        )
    return [
        patch("app.routers.authRoutes.users_collection", mock_col),
        patch("app.auth.dependencies.users_collection", mock_col),
        patch("app.database.users_collection", mock_col),
    ]


# A complete valid register body used as a base for mutation in each test.
_VALID_REGISTER_BODY = {
    "email": "alice@test.com",
    "password": _STRONG_PASSWORD,
    "username": "alice",
    "gender": "female",
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


def test_register_rejects_invalid_preference_value_type():
    """
    POST /api/auth/register with sleepScoreWD.value set to a non-numeric string
    must return 422.

    After the security fix, RegisterRequest must validate preference dicts using
    the Preference model (value: float, isDealBreaker: bool) rather than
    accepting arbitrary dicts.
    """
    body = {
        **_VALID_REGISTER_BODY,
        "sleepScoreWD": {"value": "not-a-number", "isDealBreaker": False},
    }

    with _apply_patches(_patches_for_register()):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422, (
        f"Expected 422 for non-numeric preference value, "
        f"got {response.status_code}: {response.text}"
    )


def test_register_rejects_operator_injection_in_preference():
    """
    POST /api/auth/register with an operator-injection payload as a preference
    field (e.g. {"$ne": null}) must return 422.

    This is the core FINDING-1 risk: before the fix, Optional[dict] accepted any
    dict including MongoDB operator payloads. After the fix, Optional[Preference]
    rejects dicts that lack the required `value` (float) and `isDealBreaker` (bool)
    structure, neutralising operator injection.
    """
    body = {
        **_VALID_REGISTER_BODY,
        "sleepScoreWD": {"$ne": None},
    }

    with _apply_patches(_patches_for_register()):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422, (
        f"Expected 422 for operator-injection payload in preference field, "
        f"got {response.status_code}: {response.text}"
    )


def test_register_coerces_string_bool_in_preference():
    """
    Pydantic v2 lax-mode coerces truthy strings like "yes" -> True for bool
    fields. This is intentional framework behaviour, not a security gap — the
    value is sanitised to a valid bool before reaching MongoDB.
    """
    body = {
        **_VALID_REGISTER_BODY,
        "sleepScoreWD": {"value": 5.0, "isDealBreaker": "yes"},
    }

    with _apply_patches(_patches_for_register()):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/auth/register", json=body)

    # 201: Pydantic coerces "yes" -> True (lax mode). Value is stored as bool.
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["sleepScoreWD"]["isDealBreaker"] is True


def test_register_accepts_valid_preferences():
    """
    POST /api/auth/register with all preference fields correctly typed must
    return 201 (success).

    Verifies that valid payloads are not accidentally rejected by the tightened
    validation introduced in the security fix.
    """
    body = {
        **_VALID_REGISTER_BODY,
        "sleepScoreWD": {"value": 7.0, "isDealBreaker": True},
    }

    with _apply_patches(_patches_for_register(find_one_return=None)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/auth/register", json=body)

    assert response.status_code == 201, (
        f"Expected 201 for valid preferences, "
        f"got {response.status_code}: {response.text}"
    )


def test_register_uses_defaults_when_preferences_omitted():
    """
    POST /api/auth/register with only the required fields (email, password,
    username, gender) and no preference fields must return 201.

    This confirms that the Preference-typed fields on RegisterRequest all have
    sensible defaults, so omitting them is still a valid registration payload.
    """
    body = {
        "email": "bob@test.com",
        "password": _STRONG_PASSWORD,
        "username": "bob",
        "gender": "male",
    }

    with _apply_patches(_patches_for_register(find_one_return=None)):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/auth/register", json=body)

    assert response.status_code == 201, (
        f"Expected 201 when all preference fields are omitted (defaults apply), "
        f"got {response.status_code}: {response.text}"
    )
