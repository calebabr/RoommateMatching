"""
Tests for password hashing, strength validation, and change-password endpoint.

Environment is configured before any app imports so that auth/utils.py picks up
the correct SECRET_KEY and ROOMMATCH_ENV values at module load time.
"""

import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import bcrypt
import pytest
import httpx
from httpx import ASGITransport

from app.auth.utils import hash_password, validate_password_strength
from app.main import app


# ---------------------------------------------------------------------------
# 1. bcrypt round count
# ---------------------------------------------------------------------------


class TestHashPasswordRounds:
    """Verify that hash_password uses bcrypt cost factor 12."""

    def test_bcrypt_rounds_encoded_in_hash(self):
        """The resulting hash string contains the $2b$12$ prefix."""
        hashed = hash_password("SomePassw0rd!")
        # bcrypt encodes the cost as $2b$<rounds>$
        assert hashed.startswith("$2b$12$"), (
            f"Expected hash to start with '$2b$12$', got: {hashed[:10]}"
        )

    def test_bcrypt_checkpw_verifies_hash(self):
        """bcrypt.checkpw can verify the produced hash (sanity check)."""
        plain = "AnotherP@ssw0rd"
        hashed = hash_password(plain)
        assert bcrypt.checkpw(plain.encode(), hashed.encode())

    def test_different_salts_produce_different_hashes(self):
        """Two calls with the same password produce different hashes (salt randomness)."""
        plain = "SomePassw0rd!"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2, "Two hashes of the same password should differ due to random salt"


# ---------------------------------------------------------------------------
# 2. Weak passwords rejected by validate_password_strength
# ---------------------------------------------------------------------------


class TestValidatePasswordStrengthWeak:
    """validate_password_strength raises ValueError for weak/short passwords."""

    def test_common_weak_password_raises(self):
        """'password123' is a commonly known weak password and should be rejected."""
        with pytest.raises(ValueError):
            validate_password_strength("password123")

    def test_too_short_raises(self):
        """Password shorter than MIN_PASSWORD_LENGTH (default 8) raises ValueError."""
        with pytest.raises(ValueError, match=r"at least"):
            validate_password_strength("abc")

    def test_exactly_min_length_but_weak_raises(self):
        """'12345678' meets length but has a zxcvbn score < 2, so it should raise."""
        with pytest.raises(ValueError):
            validate_password_strength("12345678")

    def test_empty_password_raises(self):
        """Empty string is clearly too short and should raise ValueError."""
        with pytest.raises(ValueError):
            validate_password_strength("")

    def test_single_char_repeated_raises(self):
        """Repeated single character is weak regardless of length."""
        with pytest.raises(ValueError):
            validate_password_strength("aaaaaaaa")


# ---------------------------------------------------------------------------
# 3. Strong passwords accepted by validate_password_strength
# ---------------------------------------------------------------------------


class TestValidatePasswordStrengthStrong:
    """validate_password_strength does NOT raise for genuinely strong passwords."""

    def test_classic_strong_password(self):
        """'Tr0ub4dor&3' is the well-known strong-password example and should pass."""
        # Should not raise
        validate_password_strength("Tr0ub4dor&3")

    def test_passphrase_style(self):
        """Long passphrase-style password should be accepted."""
        validate_password_strength("correct-horse-battery-staple")

    def test_mixed_case_symbols_digits(self):
        """Mixed uppercase, lowercase, digits, and symbols should pass."""
        validate_password_strength("G#8kLm!qR2$v")

    def test_long_random_password(self):
        """A long random-looking password should be accepted."""
        validate_password_strength("xK9#mP2@nQ5!wR7")


# ---------------------------------------------------------------------------
# 4–6. HTTP endpoint tests using httpx.AsyncClient + ASGITransport
# ---------------------------------------------------------------------------

# Strong password used to set up test users in HTTP tests
_STRONG_PASSWORD = "Tr0ub4dor&3"


@pytest.mark.asyncio
async def test_register_weak_password_returns_422():
    """POST /api/auth/register with a weak password returns HTTP 422."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "weakpw_register@auburn.edu",
                "password": "password123",
                "username": "WeakPwUser",
            },
        )
    assert response.status_code == 422, (
        f"Expected 422 for weak password at registration, got {response.status_code}: "
        f"{response.text}"
    )


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_401():
    """POST /api/auth/change-password with wrong current_password returns HTTP 401."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Register a user with a strong password
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "email": "chpw_wrong@auburn.edu",
                "password": _STRONG_PASSWORD,
                "username": "ChPwWrongUser",
            },
        )
        assert reg_resp.status_code == 201, (
            f"Setup registration failed: {reg_resp.status_code} {reg_resp.text}"
        )
        token = reg_resp.json()["access_token"]

        # Attempt change-password with an incorrect current password
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "totally-wrong-password",
                "new_password": _STRONG_PASSWORD,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401, (
        f"Expected 401 for wrong current_password, got {response.status_code}: "
        f"{response.text}"
    )
    assert "incorrect" in response.json().get("detail", "").lower(), (
        f"Expected 'incorrect' in detail, got: {response.json()}"
    )


@pytest.mark.asyncio
async def test_change_password_weak_new_password_returns_422():
    """POST /api/auth/change-password with a weak new_password returns HTTP 422."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Register a user with a strong password
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "email": "chpw_weak@auburn.edu",
                "password": _STRONG_PASSWORD,
                "username": "ChPwWeakUser",
            },
        )
        assert reg_resp.status_code == 201, (
            f"Setup registration failed: {reg_resp.status_code} {reg_resp.text}"
        )
        token = reg_resp.json()["access_token"]

        # Attempt change-password with the correct current password but a weak new one
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": _STRONG_PASSWORD,
                "new_password": "password123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422, (
        f"Expected 422 for weak new_password, got {response.status_code}: "
        f"{response.text}"
    )


@pytest.mark.asyncio
async def test_change_password_success():
    """Happy path: POST /api/auth/change-password with valid credentials returns 200."""
    new_strong_password = "G#8kLm!qR2$v"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Register a user
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "email": "chpw_success@auburn.edu",
                "password": _STRONG_PASSWORD,
                "username": "ChPwSuccessUser",
            },
        )
        assert reg_resp.status_code == 201, (
            f"Setup registration failed: {reg_resp.status_code} {reg_resp.text}"
        )
        token = reg_resp.json()["access_token"]

        # Change password successfully
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": _STRONG_PASSWORD,
                "new_password": new_strong_password,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, (
        f"Expected 200 for valid change-password, got {response.status_code}: "
        f"{response.text}"
    )
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_change_password_requires_auth():
    """POST /api/auth/change-password without a token returns 401/403."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": _STRONG_PASSWORD,
                "new_password": "G#8kLm!qR2$v",
            },
        )
    assert response.status_code in (401, 403), (
        f"Expected 401 or 403 without auth, got {response.status_code}"
    )
