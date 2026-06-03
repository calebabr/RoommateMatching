"""
IDOR integration tests for RoomMatch API.

These tests run against the real `app/main.py` FastAPI app with a live MongoDB
connection, confirming that the production `get_current_user_or_403` and
`verify_match_exists` guards actually enforce 403 on cross-user access.

Prerequisites:
  - MongoDB running on localhost:27017

Run with:
  cd backend
  pytest tests/test_idor_integration.py -v

Cleanup: all test users created here are deleted in the session-scoped teardown.
"""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import users_collection, matches_collection

BASE = "/api"

# Minimal valid preference payload required by UserCreate / authRoutes register
_PREFS = {
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


def _reg_body(tag: str) -> dict:
    return {
        "email": f"idor_test_{tag}@roommatch.test",
        "password": "TestPass123!",
        "username": f"idor_{tag}",
        "gender": "male",
        **_PREFS,
    }


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def http_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def two_users(http_client: AsyncClient):
    """Register users A and B, yield their IDs and auth headers, then clean up."""
    # Remove any leftover test accounts from a previous interrupted run
    await users_collection.delete_many(
        {"email": {"$in": [
            "idor_test_a@roommatch.test",
            "idor_test_b@roommatch.test",
            "idor_test_c@roommatch.test",
        ]}}
    )

    ra = await http_client.post(f"{BASE}/auth/register", json=_reg_body("a"))
    assert ra.status_code == 201, f"Register A failed: {ra.text}"
    rb = await http_client.post(f"{BASE}/auth/register", json=_reg_body("b"))
    assert rb.status_code == 201, f"Register B failed: {rb.text}"
    rc = await http_client.post(f"{BASE}/auth/register", json=_reg_body("c"))
    assert rc.status_code == 201, f"Register C failed: {rc.text}"

    data_a = ra.json()
    data_b = rb.json()
    data_c = rc.json()

    id_a = data_a["user"]["id"]
    id_b = data_b["user"]["id"]
    id_c = data_c["user"]["id"]

    auth_a = {"Authorization": f"Bearer {data_a['access_token']}"}
    auth_b = {"Authorization": f"Bearer {data_b['access_token']}"}

    # Insert a confirmed match record (used by verify_match_exists dependency)
    await matches_collection.insert_one({
        "user1_id": id_a,
        "user2_id": id_b,
        "status": "confirmed",
    })
    # Also set matchedWith on both user docs (used by chatService.send_message)
    await users_collection.update_one({"id": id_a}, {"$set": {"matchedWith": [id_b], "matched": True}})
    await users_collection.update_one({"id": id_b}, {"$set": {"matchedWith": [id_a], "matched": True}})

    yield {"id_a": id_a, "id_b": id_b, "id_c": id_c, "auth_a": auth_a, "auth_b": auth_b}

    # Teardown: remove test users and the match record
    await users_collection.delete_many({"id": {"$in": [id_a, id_b, id_c]}})
    await matches_collection.delete_many({
        "$or": [
            {"user1_id": id_a},
            {"user2_id": id_a},
            {"user1_id": id_b},
            {"user2_id": id_b},
        ]
    })


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_403_no_leak(r, label: str):
    assert r.status_code == 403, f"[{label}] Expected 403, got {r.status_code}: {r.text}"
    body = r.json()
    # Must not leak any user data — only a detail/error key is acceptable
    leaky_keys = {"id", "email", "username", "hashed_password", "photoUrl", "gender"}
    assert not leaky_keys.intersection(body.keys()), (
        f"[{label}] 403 body leaks user data: {body}"
    )


# ---------------------------------------------------------------------------
# Negative: user A acting on user B's resources → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idor_profile_read(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_b']}", headers=two_users["auth_a"]
    )
    _assert_403_no_leak(r, "profile_read")


@pytest.mark.asyncio
async def test_idor_profile_update(http_client, two_users):
    body = {"username": "hacker", "gender": "male", **_PREFS}
    r = await http_client.put(
        f"{BASE}/users/{two_users['id_b']}", json=body, headers=two_users["auth_a"]
    )
    _assert_403_no_leak(r, "profile_update")


@pytest.mark.asyncio
async def test_idor_profile_delete(http_client, two_users):
    r = await http_client.delete(
        f"{BASE}/users/{two_users['id_b']}", headers=two_users["auth_a"]
    )
    _assert_403_no_leak(r, "profile_delete")


@pytest.mark.asyncio
async def test_idor_like(http_client, two_users):
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_b']}/like",
        json={"toUser": two_users["id_a"]},
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "like")


@pytest.mark.asyncio
async def test_idor_unmatch(http_client, two_users):
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_b']}/unmatch/{two_users['id_a']}",
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "unmatch")


@pytest.mark.asyncio
async def test_idor_chat_send(http_client, two_users):
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_b']}/chat/{two_users['id_a']}",
        json={"content": "IDOR probe"},
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "chat_send")


@pytest.mark.asyncio
async def test_idor_chat_read(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_b']}/chat/{two_users['id_a']}",
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "chat_read")


@pytest.mark.asyncio
async def test_idor_notifications(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_b']}/notifications",
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "notifications")


@pytest.mark.asyncio
async def test_idor_upload_photo(http_client, two_users):
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 16)  # minimal JPEG header
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_b']}/upload-photo",
        files={"file": ("test.jpg", fake_image, "image/jpeg")},
        headers=two_users["auth_a"],
    )
    _assert_403_no_leak(r, "upload_photo")


# ---------------------------------------------------------------------------
# Chat-without-match: A authenticated as themselves, chatting with unmatched C → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_send_without_match(http_client, two_users):
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_a']}/chat/{two_users['id_c']}",
        json={"content": "no match probe"},
        headers=two_users["auth_a"],
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_chat_read_without_match(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_a']}/chat/{two_users['id_c']}",
        headers=two_users["auth_a"],
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Positive: user A acting on their own resources → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_own_profile_read(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_a']}", headers=two_users["auth_a"]
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_own_notifications(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_a']}/notifications",
        headers=two_users["auth_a"],
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_own_chat_send_with_match(http_client, two_users):
    r = await http_client.post(
        f"{BASE}/users/{two_users['id_a']}/chat/{two_users['id_b']}",
        json={"content": "hello from integration test"},
        headers=two_users["auth_a"],
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_own_chat_read_with_match(http_client, two_users):
    r = await http_client.get(
        f"{BASE}/users/{two_users['id_a']}/chat/{two_users['id_b']}",
        headers=two_users["auth_a"],
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
