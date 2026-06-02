"""
Validation hardening tests for RoomMatch — Task B2.

Tests verify that the spec-defined validation constraints are enforced on:
  - POST /api/auth/register
  - PUT /api/users/{user_id}
  - POST /api/users/{user_id}/chat/{partner_id}

These tests are written to the *spec*, not the current (unvalidated) code.
They are expected to pass only after the Backend Agent implements the
validation hardening described in the spec.

Run with:
    cd backend
    pytest test_validation.py -v
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
import json
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
# Shared helpers / constants
# ---------------------------------------------------------------------------

_STRONG_PASSWORD = "Tr0ub4dor&3"

# Minimal Preference dict used throughout the tests
_VALID_PREF = {"value": 5.0, "isDealBreaker": False}

# A complete, valid register body used as a base for mutation in each test.
_VALID_REGISTER_BODY = {
    "email": "testuser@test.com",
    "password": _STRONG_PASSWORD,
    "username": "testuser",
    "gender": "female",
    "bio": "Just a normal bio.",
    "lifestyleTags": ["early_bird", "social"],
    "sleepScoreWD": _VALID_PREF,
    "sleepScoreWE": _VALID_PREF,
    "cleanlinessScore": _VALID_PREF,
    "noiseToleranceScore": _VALID_PREF,
    "guestsScore": _VALID_PREF,
    "personalityScore": _VALID_PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _VALID_PREF,
    "communicationScore": _VALID_PREF,
}

# A complete, valid UserCreate body for PUT /api/users/{user_id}
_VALID_USER_CREATE_BODY = {
    "username": "testuser",
    "gender": "female",
    "bio": "Normal bio.",
    "lifestyleTags": ["early_bird", "social"],
    "sleepScoreWD": _VALID_PREF,
    "sleepScoreWE": _VALID_PREF,
    "cleanlinessScore": _VALID_PREF,
    "noiseToleranceScore": _VALID_PREF,
    "guestsScore": _VALID_PREF,
    "personalityScore": _VALID_PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _VALID_PREF,
    "communicationScore": _VALID_PREF,
}

# A fake stored user document returned by the auth dependency's find_one call.
_FAKE_AUTH_USER = {
    "id": 1,
    "username": "testuser",
    "email": "testuser@test.com",
    "hashed_password": "hashed",
    "gender": "female",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [2],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "sleepScoreWD": _VALID_PREF,
    "sleepScoreWE": _VALID_PREF,
    "cleanlinessScore": _VALID_PREF,
    "noiseToleranceScore": _VALID_PREF,
    "guestsScore": _VALID_PREF,
    "personalityScore": _VALID_PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _VALID_PREF,
    "communicationScore": _VALID_PREF,
}

# A minimal user response dict that satisfies UserResponse validation.
_FAKE_USER_RESPONSE = {
    "id": 1,
    "username": "testuser",
    "email": "testuser@test.com",
    "gender": "female",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
    "bio": "",
    "photoUrl": "",
    "lifestyleTags": [],
    "sleepScoreWD": _VALID_PREF,
    "sleepScoreWE": _VALID_PREF,
    "cleanlinessScore": _VALID_PREF,
    "noiseToleranceScore": _VALID_PREF,
    "guestsScore": _VALID_PREF,
    "personalityScore": _VALID_PREF,
    "smokingScore": {"value": 0.0, "isDealBreaker": False},
    "sharedSpaceScore": _VALID_PREF,
    "communicationScore": _VALID_PREF,
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
# Patch helpers for register tests
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


# ---------------------------------------------------------------------------
# Patch helpers for PUT /api/users/{user_id} tests
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


# ---------------------------------------------------------------------------
# Patch helpers for chat tests
# ---------------------------------------------------------------------------

def _patches_for_chat(send_message_mock: AsyncMock):
    """Return patches for the chat endpoint tests."""
    auth_col = _make_mock_collection()
    auth_col.find_one = AsyncMock(return_value=dict(_FAKE_AUTH_USER))

    matches_col = _make_mock_collection()
    # Make matches_collection.find_one return a fake match so verify_match_exists passes
    matches_col.find_one = AsyncMock(return_value={
        "user1_id": 1, "user2_id": 2, "compatibilityScore": 0.9
    })

    return [
        patch("app.auth.dependencies.users_collection", auth_col),
        patch("app.auth.dependencies.matches_collection", matches_col),
        patch("app.database.users_collection", auth_col),
        patch(
            "app.routers.userRoutes.chatService.send_message",
            send_message_mock,
        ),
    ]


# ===========================================================================
# Helper: assert 422 error format
# ===========================================================================

def _assert_422_with_field_message_format(response):
    """Assert response is 422 and detail list contains field+message items."""
    assert response.status_code == 422, (
        f"Expected 422, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert "detail" in data, f"Response missing 'detail' key: {data}"
    detail = data["detail"]
    assert isinstance(detail, list), f"Expected 'detail' to be a list, got: {type(detail)}"
    assert len(detail) > 0, "Expected at least one error item in 'detail'"
    for item in detail:
        assert "field" in item, (
            f"Error item missing 'field' key: {item}. "
            f"Internal Pydantic paths must not be leaked."
        )
        assert "message" in item, (
            f"Error item missing 'message' key: {item}"
        )
        # Ensure internal schema paths like "body.username" or "body -> username" are not leaked
        field_val = item["field"]
        assert not field_val.startswith("body."), (
            f"'field' must not leak internal path 'body.*': got '{field_val}'"
        )
        assert " -> " not in field_val or field_val.count(" -> ") == 0, (
            f"'field' must not contain internal Pydantic path arrows: got '{field_val}'"
        )


# ===========================================================================
# Register endpoint — negative-path tests
# ===========================================================================

class TestRegisterUsernameValidation:

    def test_register_username_too_long(self):
        """username > 30 chars must return 422."""
        body = {**_VALID_REGISTER_BODY, "username": "a" * 31}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for username > 30 chars, got {response.status_code}: {response.text}"
        )

    def test_register_username_with_spaces(self):
        """username containing spaces must return 422 (pattern ^[A-Za-z0-9_-]+$)."""
        body = {**_VALID_REGISTER_BODY, "username": "invalid user"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for username with spaces, got {response.status_code}: {response.text}"
        )

    def test_register_username_invalid_chars(self):
        """username containing <> must return 422."""
        body = {**_VALID_REGISTER_BODY, "username": "user<>name"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for username with <> chars, got {response.status_code}: {response.text}"
        )

    def test_register_username_with_script_tag(self):
        """username '<script>xss</script>' must return 422 (invalid chars in pattern)."""
        body = {**_VALID_REGISTER_BODY, "username": "<script>xss</script>"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for script-tag username, got {response.status_code}: {response.text}"
        )


class TestRegisterBioValidation:

    def test_register_bio_too_long(self):
        """bio > 500 chars must return 422."""
        body = {**_VALID_REGISTER_BODY, "bio": "x" * 501}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for bio > 500 chars, got {response.status_code}: {response.text}"
        )

    def test_register_bio_html_stripped(self):
        """bio '<b>hello</b>' must be accepted (201) with tags stripped to 'hello'."""
        body = {**_VALID_REGISTER_BODY, "bio": "<b>hello</b>"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 (tags stripped, not rejected), got {response.status_code}: {response.text}"
        )
        data = response.json()
        bio_stored = data.get("user", {}).get("bio", "")
        assert bio_stored == "hello", (
            f"Expected bio stored as 'hello' after tag stripping, got: '{bio_stored}'"
        )

    def test_register_bio_script_stripped(self):
        """bio '<script>alert(1)</script>safe' must be accepted (201) with bio stored as 'safe'."""
        body = {**_VALID_REGISTER_BODY, "bio": "<script>alert(1)</script>safe"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 (script tags stripped, not rejected), got {response.status_code}: {response.text}"
        )
        data = response.json()
        bio_stored = data.get("user", {}).get("bio", "")
        assert bio_stored == "safe", (
            f"Expected bio stored as 'safe' after script-tag stripping, got: '{bio_stored}'"
        )


class TestRegisterGenderValidation:

    def test_register_invalid_gender(self):
        """gender 'attack' must return 422 (only 'male', 'female', or '' allowed)."""
        body = {**_VALID_REGISTER_BODY, "gender": "attack"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for gender='attack', got {response.status_code}: {response.text}"
        )

    def test_register_valid_gender_male(self):
        """gender 'male' must be accepted (201)."""
        body = {**_VALID_REGISTER_BODY, "username": "maleuser", "email": "male@test.com", "gender": "male"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for valid gender='male', got {response.status_code}: {response.text}"
        )

    def test_register_valid_gender_female(self):
        """gender 'female' must be accepted (201)."""
        body = {**_VALID_REGISTER_BODY, "gender": "female"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for valid gender='female', got {response.status_code}: {response.text}"
        )


class TestRegisterLifestyleTagsValidation:

    def test_register_invalid_lifestyle_tag(self):
        """lifestyleTags containing 'hacker' (not in whitelist) must return 422."""
        body = {**_VALID_REGISTER_BODY, "lifestyleTags": ["hacker"]}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for invalid lifestyle tag 'hacker', got {response.status_code}: {response.text}"
        )

    def test_register_too_many_lifestyle_tags(self):
        """lifestyleTags with 11 valid tags must return 422 (max 10)."""
        # All 11 are valid whitelist entries
        eleven_tags = [
            "early_bird", "night_owl", "light_sleeper", "heavy_sleeper",
            "neat_freak", "relaxed_cleaner", "social", "introverted",
            "pet_friendly", "no_pets", "smoker",
        ]
        assert len(eleven_tags) == 11
        body = {**_VALID_REGISTER_BODY, "lifestyleTags": eleven_tags}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for 11 lifestyle tags (max 10), got {response.status_code}: {response.text}"
        )

    def test_register_exactly_ten_lifestyle_tags_accepted(self):
        """lifestyleTags with exactly 10 valid tags must be accepted (201)."""
        ten_tags = [
            "early_bird", "night_owl", "light_sleeper", "heavy_sleeper",
            "neat_freak", "relaxed_cleaner", "social", "introverted",
            "pet_friendly", "no_pets",
        ]
        assert len(ten_tags) == 10
        body = {**_VALID_REGISTER_BODY, "lifestyleTags": ten_tags}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for exactly 10 valid lifestyle tags, got {response.status_code}: {response.text}"
        )


class TestRegisterPreferenceScoreValidation:

    def test_register_preference_score_above_max(self):
        """sleepScoreWD.value = 11.0 must return 422 (max is 10.0)."""
        body = {
            **_VALID_REGISTER_BODY,
            "sleepScoreWD": {"value": 11.0, "isDealBreaker": False},
        }
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for preference value=11.0 (above max 10.0), "
            f"got {response.status_code}: {response.text}"
        )

    def test_register_preference_score_below_min(self):
        """sleepScoreWD.value = -1.0 must return 422 (min is 0.0)."""
        body = {
            **_VALID_REGISTER_BODY,
            "sleepScoreWD": {"value": -1.0, "isDealBreaker": False},
        }
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422, (
            f"Expected 422 for preference value=-1.0 (below min 0.0), "
            f"got {response.status_code}: {response.text}"
        )

    def test_register_preference_score_at_boundary_zero(self):
        """sleepScoreWD.value = 0.0 (boundary) must be accepted (201)."""
        body = {
            **_VALID_REGISTER_BODY,
            "sleepScoreWD": {"value": 0.0, "isDealBreaker": False},
        }
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for preference value=0.0 (inclusive boundary), "
            f"got {response.status_code}: {response.text}"
        )

    def test_register_preference_score_at_boundary_ten(self):
        """sleepScoreWD.value = 10.0 (boundary) must be accepted (201)."""
        body = {
            **_VALID_REGISTER_BODY,
            "sleepScoreWD": {"value": 10.0, "isDealBreaker": False},
        }
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for preference value=10.0 (inclusive boundary), "
            f"got {response.status_code}: {response.text}"
        )

    def test_register_preference_score_at_boundary(self):
        """Both value=0.0 and value=10.0 must be accepted in a single test pass."""
        for boundary_val in (0.0, 10.0):
            body = {
                **_VALID_REGISTER_BODY,
                "sleepScoreWD": {"value": boundary_val, "isDealBreaker": False},
            }
            with _apply_patches(_patches_for_register(find_one_return=None)):
                client = TestClient(app, raise_server_exceptions=False)
                response = client.post("/api/auth/register", json=body)
            assert response.status_code == 201, (
                f"Expected 201 for preference value={boundary_val} (boundary), "
                f"got {response.status_code}: {response.text}"
            )


# ===========================================================================
# PUT /api/users/{user_id} — negative-path tests
# ===========================================================================

class TestUpdateProfileValidation:

    def test_update_profile_username_too_long(self):
        """PUT /api/users/1 with username > 30 chars must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "username": "u" * 31}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for username > 30 chars on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_username_invalid_chars(self):
        """PUT /api/users/1 with username containing <> must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "username": "bad<>user"}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for invalid username chars on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_bio_too_long(self):
        """PUT /api/users/1 with bio > 500 chars must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "bio": "x" * 501}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for bio > 500 chars on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_bio_html_stripped(self):
        """PUT /api/users/1 with bio '<b>hello</b>' must succeed (200) with bio stored as 'hello'."""
        # The update_profile mock returns a response with bio already stripped.
        stripped_response = dict(_FAKE_USER_RESPONSE)
        stripped_response["bio"] = "hello"
        update_mock = AsyncMock(return_value=stripped_response)
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "bio": "<b>hello</b>"}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200, (
            f"Expected 200 (HTML in bio stripped, not rejected) on PUT, "
            f"got {response.status_code}: {response.text}"
        )
        # Verify the value passed to update_profile had HTML stripped
        assert update_mock.called, "update_profile was never called"
        _, call_args, _ = update_mock.mock_calls[0]
        passed_dict = call_args[1]
        bio_passed = passed_dict.get("bio", "")
        assert bio_passed == "hello", (
            f"Expected bio passed to update_profile as 'hello' after stripping, got: '{bio_passed}'"
        )

    def test_update_profile_invalid_gender(self):
        """PUT /api/users/1 with gender 'unknown' must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "gender": "unknown"}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for invalid gender on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_invalid_lifestyle_tag(self):
        """PUT /api/users/1 with invalid lifestyle tag must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "lifestyleTags": ["hacker"]}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for invalid lifestyle tag on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_too_many_lifestyle_tags(self):
        """PUT /api/users/1 with 11 lifestyle tags must return 422 (max 10)."""
        eleven_tags = [
            "early_bird", "night_owl", "light_sleeper", "heavy_sleeper",
            "neat_freak", "relaxed_cleaner", "social", "introverted",
            "pet_friendly", "no_pets", "smoker",
        ]
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "lifestyleTags": eleven_tags}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for 11 lifestyle tags on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_preference_score_above_max(self):
        """PUT /api/users/1 with cleanlinessScore.value = 11.0 must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "cleanlinessScore": {"value": 11.0, "isDealBreaker": False}}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for preference value=11.0 on PUT, got {response.status_code}: {response.text}"
        )

    def test_update_profile_preference_score_below_min(self):
        """PUT /api/users/1 with cleanlinessScore.value = -1.0 must return 422."""
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)
        body = {**_VALID_USER_CREATE_BODY, "cleanlinessScore": {"value": -1.0, "isDealBreaker": False}}

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for preference value=-1.0 on PUT, got {response.status_code}: {response.text}"
        )


# ===========================================================================
# Chat message tests
# ===========================================================================

class TestChatMessageValidation:

    def test_chat_message_too_long(self):
        """POST /api/users/1/chat/2 with content > 1000 chars must return 422."""
        send_mock = AsyncMock(return_value={
            "id": "abc123",
            "fromUser": 1,
            "toUser": 2,
            "content": "x" * 1000,
            "createdAt": "2024-01-01T00:00:00",
        })
        token = _make_auth_token(1)
        body = {"content": "x" * 1001}

        with _apply_patches(_patches_for_chat(send_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/users/1/chat/2",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for chat content > 1000 chars, got {response.status_code}: {response.text}"
        )

    def test_chat_message_empty_content(self):
        """POST /api/users/1/chat/2 with empty string content must return 422 (min_length=1)."""
        send_mock = AsyncMock(return_value={
            "id": "abc123", "fromUser": 1, "toUser": 2,
            "content": "", "createdAt": "2024-01-01T00:00:00",
        })
        token = _make_auth_token(1)
        body = {"content": ""}

        with _apply_patches(_patches_for_chat(send_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/users/1/chat/2",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422, (
            f"Expected 422 for empty chat content, got {response.status_code}: {response.text}"
        )

    def test_chat_message_html_stripped(self):
        """POST /api/users/1/chat/2 with '<b>hi</b>' must succeed (200) with content stored as 'hi'."""
        send_mock = AsyncMock(return_value={
            "id": "abc123",
            "fromUser": 1,
            "toUser": 2,
            "content": "hi",
            "createdAt": "2024-01-01T00:00:00",
        })
        token = _make_auth_token(1)
        body = {"content": "<b>hi</b>"}

        with _apply_patches(_patches_for_chat(send_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/users/1/chat/2",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200, (
            f"Expected 200 (HTML in chat content stripped, not rejected), "
            f"got {response.status_code}: {response.text}"
        )
        # Verify the content passed to send_message was stripped
        assert send_mock.called, "chatService.send_message was never called"
        _, call_args, _ = send_mock.mock_calls[0]
        # send_message(user_id, partner_id, message.content) — content is 3rd positional arg
        content_passed = call_args[2]
        assert content_passed == "hi", (
            f"Expected content passed to send_message as 'hi' after HTML stripping, "
            f"got: '{content_passed}'"
        )

    def test_chat_message_script_tag_stripped(self):
        """POST /api/users/1/chat/2 with script injection must succeed with script stripped."""
        send_mock = AsyncMock(return_value={
            "id": "abc123",
            "fromUser": 1,
            "toUser": 2,
            "content": "hello",
            "createdAt": "2024-01-01T00:00:00",
        })
        token = _make_auth_token(1)
        body = {"content": "<script>alert(1)</script>hello"}

        with _apply_patches(_patches_for_chat(send_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/users/1/chat/2",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200, (
            f"Expected 200 (script stripped from chat content, not rejected), "
            f"got {response.status_code}: {response.text}"
        )
        assert send_mock.called, "chatService.send_message was never called"
        _, call_args, _ = send_mock.mock_calls[0]
        content_passed = call_args[2]
        assert content_passed == "hello", (
            f"Expected content='hello' after script stripping, got: '{content_passed}'"
        )


# ===========================================================================
# Body size limit tests
# ===========================================================================

class TestBodySizeLimit:

    def test_body_size_limit_register(self):
        """
        POST /api/auth/register with Content-Length header > 1 MB must return 413.

        The middleware checks the Content-Length header (doesn't need a real 1MB body),
        so we send a small body but spoof the header value.
        """
        oversized_length = str(1 * 1024 * 1024 + 1)  # 1 MB + 1 byte
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/api/auth/register",
                json=_VALID_REGISTER_BODY,
                headers={"Content-Length": oversized_length},
            )
        assert response.status_code == 413, (
            f"Expected 413 for body > 1MB, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data.get("detail") == "Request body too large", (
            f"Expected detail='Request body too large', got: {data}"
        )

    def test_body_size_limit_update_profile(self):
        """
        PUT /api/users/1 with Content-Length header > 1 MB must return 413.
        """
        oversized_length = str(1 * 1024 * 1024 + 1)
        update_mock = AsyncMock(return_value=dict(_FAKE_USER_RESPONSE))
        get_all_mock = AsyncMock(return_value=[])
        token = _make_auth_token(1)

        with _apply_patches(_patches_for_put(update_mock, get_all_mock)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.put(
                "/api/users/1",
                json=_VALID_USER_CREATE_BODY,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Length": oversized_length,
                },
            )
        assert response.status_code == 413, (
            f"Expected 413 for body > 1MB on PUT, got {response.status_code}: {response.text}"
        )


# ===========================================================================
# HTML injection sanitization tests
# ===========================================================================

class TestHtmlSanitization:

    def test_register_bio_only_script_content_stripped_to_empty(self):
        """
        bio consisting entirely of a script tag must be stored as empty string.
        The request must succeed (not be rejected), returned bio should be ''.
        """
        body = {**_VALID_REGISTER_BODY, "bio": "<script>evil()</script>"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 (script-only bio stripped to empty, not rejected), "
            f"got {response.status_code}: {response.text}"
        )
        bio_stored = response.json().get("user", {}).get("bio", None)
        assert bio_stored == "", (
            f"Expected bio stored as '' (empty after stripping script), got: '{bio_stored}'"
        )

    def test_register_bio_nested_html_stripped(self):
        """
        bio with nested HTML like '<div><b>text</b></div>' must store only 'text'.
        """
        body = {**_VALID_REGISTER_BODY, "bio": "<div><b>text</b></div>"}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 (nested HTML stripped), got {response.status_code}: {response.text}"
        )
        bio_stored = response.json().get("user", {}).get("bio", None)
        assert bio_stored == "text", (
            f"Expected bio stored as 'text' after stripping nested HTML, got: '{bio_stored}'"
        )

    def test_register_plain_text_bio_unchanged(self):
        """
        bio with no HTML must be stored verbatim (no transformation of plain text).
        """
        plain_bio = "I love Auburn University and co-op programs!"
        body = {**_VALID_REGISTER_BODY, "bio": plain_bio}
        with _apply_patches(_patches_for_register(find_one_return=None)):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, (
            f"Expected 201 for plain-text bio, got {response.status_code}: {response.text}"
        )
        bio_stored = response.json().get("user", {}).get("bio", None)
        assert bio_stored == plain_bio, (
            f"Expected plain-text bio stored unchanged, got: '{bio_stored}'"
        )


# ===========================================================================
# Validation error format tests
# ===========================================================================

class TestValidationErrorFormat:

    def test_validation_error_format_username(self):
        """
        Any 422 response must have {'detail': [{'field': ..., 'message': ...}]}.
        Internal Pydantic paths like 'body.username' or 'body -> username' must not appear.
        """
        body = {**_VALID_REGISTER_BODY, "username": "<bad>"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        _assert_422_with_field_message_format(response)

    def test_validation_error_format_preference_value(self):
        """
        422 for an out-of-range preference value must use clean field/message format.
        """
        body = {
            **_VALID_REGISTER_BODY,
            "sleepScoreWD": {"value": 99.0, "isDealBreaker": False},
        }
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        _assert_422_with_field_message_format(response)

    def test_validation_error_format_lifestyle_tag(self):
        """
        422 for an invalid lifestyle tag must use clean field/message format.
        """
        body = {**_VALID_REGISTER_BODY, "lifestyleTags": ["invalid_tag_xyz"]}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        _assert_422_with_field_message_format(response)

    def test_validation_error_format_gender(self):
        """
        422 for an invalid gender must use clean field/message format.
        """
        body = {**_VALID_REGISTER_BODY, "gender": "robot"}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        _assert_422_with_field_message_format(response)

    def test_validation_error_no_pydantic_path_leaked(self):
        """
        422 responses must not contain raw Pydantic internal location paths
        (e.g., 'body', 'body.username', 'body -> username') in the 'field' value.
        """
        body = {**_VALID_REGISTER_BODY, "username": "a" * 31}
        with _apply_patches(_patches_for_register()):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/api/auth/register", json=body)
        assert response.status_code == 422
        data = response.json()
        raw_text = json.dumps(data)
        # The raw response should not expose the Pydantic internal path format
        assert "body -> " not in raw_text, (
            f"Pydantic internal path arrows 'body -> ' leaked in error response: {raw_text}"
        )
