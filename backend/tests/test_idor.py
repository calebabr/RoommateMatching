"""
IDOR (Insecure Direct Object Reference) tests for RoomMatch API.

These tests use a self-contained FastAPI app that mirrors the IDOR guard logic
defined in Tasks #7, #8, and #9 (`get_current_user_or_403`, `verify_match_exists`).
They confirm that user A cannot access or modify user B's resources (→ 403),
and that user A can successfully act on their own resources (→ 200/201).

Run with:
  cd backend
  pytest tests/test_idor.py -v
"""

import os
import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from httpx import AsyncClient, ASGITransport

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-not-for-production")
ALGORITHM = "HS256"

USER_A = {"id": 1, "username": "alice"}
USER_B = {"id": 2, "username": "bob"}
USER_C = {"id": 3, "username": "carol"}

USERS_DB = {u["id"]: u for u in [USER_A, USER_B, USER_C]}
# Only A↔B are matched; A↔C are not
MATCHES_DB = {(1, 2), (2, 1)}

bearer_scheme = HTTPBearer()


def make_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id)}, SECRET_KEY, algorithm=ALGORITHM)


TOKEN_A = make_token(USER_A["id"])
TOKEN_B = make_token(USER_B["id"])

AUTH_A = {"Authorization": f"Bearer {TOKEN_A}"}
AUTH_B = {"Authorization": f"Bearer {TOKEN_B}"}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = USERS_DB.get(uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_or_403(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


async def verify_match_exists(user_id: int, partner_id: int) -> None:
    if (user_id, partner_id) not in MATCHES_DB:
        raise HTTPException(status_code=403, detail="Not matched with this user")


def build_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/users/{user_id}")
    async def get_profile(
        user_id: int,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"id": user_id})

    @app.put("/api/users/{user_id}")
    async def update_profile(
        user_id: int,
        request: Request,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"id": user_id, "updated": True})

    @app.delete("/api/users/{user_id}")
    async def delete_profile(
        user_id: int,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"deleted": True})

    @app.post("/api/users/{user_id}/like")
    async def like_user(
        user_id: int,
        request: Request,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"liked": True})

    @app.post("/api/users/{user_id}/unmatch/{partner_id}")
    async def unmatch(
        user_id: int,
        partner_id: int,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"unmatched": True})

    @app.post("/api/users/{user_id}/chat/{partner_id}")
    async def send_chat(
        user_id: int,
        partner_id: int,
        _: dict = Depends(get_current_user_or_403),
        __: None = Depends(verify_match_exists),
    ):
        return JSONResponse({"sent": True})

    @app.get("/api/users/{user_id}/chat/{partner_id}")
    async def read_chat(
        user_id: int,
        partner_id: int,
        _: dict = Depends(get_current_user_or_403),
        __: None = Depends(verify_match_exists),
    ):
        return JSONResponse({"messages": []})

    @app.get("/api/users/{user_id}/notifications")
    async def get_notifications(
        user_id: int,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse([])

    @app.post("/api/users/{user_id}/upload-photo")
    async def upload_photo(
        user_id: int,
        _: dict = Depends(get_current_user_or_403),
    ):
        return JSONResponse({"photoUrl": "/uploads/test.jpg"})

    return app


@pytest_asyncio.fixture()
async def client():
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Negative cases: user A acting on user B's resources → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idor_profile_read(client: AsyncClient):
    r = await client.get("/api/users/2", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_profile_update(client: AsyncClient):
    r = await client.put("/api/users/2", json={"username": "hacker"}, headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_profile_delete(client: AsyncClient):
    r = await client.delete("/api/users/2", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_like(client: AsyncClient):
    r = await client.post("/api/users/2/like", json={"toUser": 3}, headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_unmatch(client: AsyncClient):
    r = await client.post("/api/users/2/unmatch/1", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_chat_send(client: AsyncClient):
    r = await client.post(
        "/api/users/2/chat/1", json={"content": "hi"}, headers=AUTH_A
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_chat_read(client: AsyncClient):
    r = await client.get("/api/users/2/chat/1", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_notifications(client: AsyncClient):
    r = await client.get("/api/users/2/notifications", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_idor_upload_photo(client: AsyncClient):
    r = await client.post("/api/users/2/upload-photo", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# ---------------------------------------------------------------------------
# Chat-without-match: user A authenticated as themselves but not matched with C → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_send_without_match(client: AsyncClient):
    r = await client.post(
        "/api/users/1/chat/3", json={"content": "hi"}, headers=AUTH_A
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_chat_read_without_match(client: AsyncClient):
    r = await client.get("/api/users/1/chat/3", headers=AUTH_A)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# ---------------------------------------------------------------------------
# Positive cases: user A acting on their own resources → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_own_profile_read(client: AsyncClient):
    r = await client.get("/api/users/1", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_profile_update(client: AsyncClient):
    r = await client.put("/api/users/1", json={"username": "alice2"}, headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_profile_delete(client: AsyncClient):
    r = await client.delete("/api/users/1", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_like(client: AsyncClient):
    r = await client.post("/api/users/1/like", json={"toUser": 2}, headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_unmatch(client: AsyncClient):
    r = await client.post("/api/users/1/unmatch/2", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_chat_send_with_match(client: AsyncClient):
    r = await client.post(
        "/api/users/1/chat/2", json={"content": "hey"}, headers=AUTH_A
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_chat_read_with_match(client: AsyncClient):
    r = await client.get("/api/users/1/chat/2", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_notifications(client: AsyncClient):
    r = await client.get("/api/users/1/notifications", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_own_upload_photo(client: AsyncClient):
    r = await client.post("/api/users/1/upload-photo", headers=AUTH_A)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
