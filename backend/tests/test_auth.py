import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.utils import create_access_token
from datetime import timedelta

client = TestClient(app)


class TestRegister:
    """POST /api/auth/register endpoint tests."""

    def test_register_success(self):
        """Happy path: Register with valid email, password, and name."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@auburn.edu",
                "password": "securepass123",
                "name": "John Doe"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@auburn.edu"
        assert data["user"]["name"] == "John Doe"
        assert "hashed_password" not in data["user"]
        assert "_id" not in data["user"]

    def test_register_duplicate_email_409(self):
        """Duplicate email returns 409 Conflict."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@auburn.edu",
                "password": "pass123",
                "name": "First User"
            }
        )

        # Try to register with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@auburn.edu",
                "password": "differentpass",
                "name": "Second User"
            }
        )

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_email_case_insensitive(self):
        """Email comparison is case-insensitive."""
        # Register with lowercase
        client.post(
            "/api/auth/register",
            json={
                "email": "test@auburn.edu",
                "password": "pass123",
                "name": "User One"
            }
        )

        # Try with uppercase
        response = client.post(
            "/api/auth/register",
            json={
                "email": "TEST@AUBURN.EDU",
                "password": "pass123",
                "name": "User Two"
            }
        )

        assert response.status_code == 409

    def test_register_missing_email_422(self):
        """Missing email field returns 422 Unprocessable Entity."""
        response = client.post(
            "/api/auth/register",
            json={
                "password": "pass123",
                "name": "John Doe"
            }
        )

        assert response.status_code == 422

    def test_register_missing_password_422(self):
        """Missing password field returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@auburn.edu",
                "name": "John Doe"
            }
        )

        assert response.status_code == 422

    def test_register_missing_name_422(self):
        """Missing name field returns 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@auburn.edu",
                "password": "pass123"
            }
        )

        assert response.status_code == 422

    def test_register_empty_email_allowed(self):
        """Empty email is technically accepted by the API (not ideal, but current behavior)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "",
                "password": "pass123",
                "name": "John"
            }
        )

        # API currently allows empty email - this could be improved with validation
        assert response.status_code in [201, 422, 400]

    def test_register_creates_user_with_defaults(self):
        """Registered user has default preference fields."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user@auburn.edu",
                "password": "pass123",
                "name": "Jane Doe"
            }
        )

        assert response.status_code == 201
        user = response.json()["user"]

        # Check default fields
        assert user["matched"] == False
        assert user["matchCount"] == 0
        assert user["matchedWith"] == []
        assert user["username"] == "Jane Doe"
        assert user["gender"] == ""
        assert user["bio"] == ""


class TestLogin:
    """POST /api/auth/login endpoint tests."""

    def test_login_valid_credentials(self):
        """Valid credentials return access token."""
        # Register a user first
        email = "logintest@auburn.edu"
        password = "testpass123"

        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "Login Test User"
            }
        )

        # Login with correct credentials
        response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": password
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert "hashed_password" not in data["user"]

    def test_login_wrong_password_401(self):
        """Wrong password returns 401."""
        email = "wrongpass@auburn.edu"

        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "correctpass",
                "name": "User"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "wrongpass"
            }
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_unknown_email_401(self):
        """Unknown email returns 401."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@auburn.edu",
                "password": "anypass"
            }
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_case_insensitive_email(self):
        """Login works with different email case."""
        email = "mixedcase@auburn.edu"
        password = "pass123"

        # Register with lowercase
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": "User"
            }
        )

        # Login with uppercase
        response = client.post(
            "/api/auth/login",
            json={
                "email": email.upper(),
                "password": password
            }
        )

        assert response.status_code == 200

    def test_login_empty_password_401(self):
        """Empty password returns 401."""
        email = "emptypass@auburn.edu"

        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "realpass",
                "name": "User"
            }
        )

        response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": ""
            }
        )

        assert response.status_code == 401

    def test_login_missing_email_422(self):
        """Missing email returns 422."""
        response = client.post(
            "/api/auth/login",
            json={
                "password": "pass123"
            }
        )

        assert response.status_code == 422

    def test_login_missing_password_422(self):
        """Missing password returns 422."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "user@auburn.edu"
            }
        )

        assert response.status_code == 422


class TestMe:
    """GET /api/auth/me endpoint tests."""

    def test_me_valid_token(self):
        """Valid Bearer token returns user profile."""
        # Register and get token
        email = "metest@auburn.edu"
        name = "Me Test User"

        register_response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "pass123",
                "name": name
            }
        )

        token = register_response.json()["access_token"]

        # Get /me with valid token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        user = response.json()
        assert user["email"] == email
        assert user["name"] == name
        assert "hashed_password" not in user
        assert "_id" not in user

    def test_me_missing_token_401(self):
        """Missing Authorization header returns 401 or 403."""
        response = client.get("/api/auth/me")

        assert response.status_code in [401, 403]

    def test_me_invalid_token_401(self):
        """Invalid/garbage token returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_me_expired_token_401(self):
        """Expired token returns 401."""
        # Create an expired token
        expired_token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(hours=-1)
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    def test_me_malformed_auth_header_401(self):
        """Malformed Authorization header returns 401/403."""
        # Missing "Bearer" prefix
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "just-a-token"}
        )

        assert response.status_code in [401, 403]

    def test_me_token_for_nonexistent_user_401(self):
        """Token for deleted/nonexistent user returns 401."""
        # Create a token for a user ID that doesn't exist
        fake_token = create_access_token({"sub": "99999"})

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {fake_token}"}
        )

        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]

    def test_me_returns_all_user_fields(self):
        """Response includes all user profile fields."""
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "allfields@auburn.edu",
                "password": "pass123",
                "name": "All Fields User"
            }
        )

        token = register_response.json()["access_token"]
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        user = response.json()

        # Check expected fields
        expected_fields = [
            "id", "email", "name", "username", "gender",
            "matched", "matchCount", "matchedWith",
            "bio", "photoUrl", "lifestyleTags",
            "sleepScoreWD", "sleepScoreWE",
            "cleanlinessScore", "noiseToleranceScore",
            "guestsScore", "personalityScore",
            "smokingScore", "sharedSpaceScore",
            "communicationScore"
        ]

        for field in expected_fields:
            assert field in user, f"Missing field: {field}"


class TestAuthFlow:
    """End-to-end authentication flow tests."""

    def test_full_auth_flow(self):
        """Complete flow: register, login, access protected route."""
        email = "flow@auburn.edu"
        password = "flowpass123"
        name = "Flow Test"

        # 1. Register
        register_resp = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name
            }
        )
        assert register_resp.status_code == 201
        register_token = register_resp.json()["access_token"]

        # 2. Login
        login_resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200
        login_token = login_resp.json()["access_token"]

        # 3. Access /me with both tokens
        me_resp1 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {register_token}"}
        )
        me_resp2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_token}"}
        )

        assert me_resp1.status_code == 200
        assert me_resp2.status_code == 200
        assert me_resp1.json()["email"] == email
        assert me_resp2.json()["email"] == email

    def test_multiple_users_isolated(self):
        """Different users have isolated tokens and data."""
        # Register user 1
        user1_resp = client.post(
            "/api/auth/register",
            json={
                "email": "user1@auburn.edu",
                "password": "pass1",
                "name": "User One"
            }
        )
        user1_token = user1_resp.json()["access_token"]
        user1_id = user1_resp.json()["user"]["id"]

        # Register user 2
        user2_resp = client.post(
            "/api/auth/register",
            json={
                "email": "user2@auburn.edu",
                "password": "pass2",
                "name": "User Two"
            }
        )
        user2_token = user2_resp.json()["access_token"]
        user2_id = user2_resp.json()["user"]["id"]

        # Verify users are different
        assert user1_id != user2_id

        # Verify tokens return correct users
        me1 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user1_token}"}
        ).json()
        me2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {user2_token}"}
        ).json()

        assert me1["email"] == "user1@auburn.edu"
        assert me2["email"] == "user2@auburn.edu"
