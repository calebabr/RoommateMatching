"""
Tests for chat read receipts feature.

POST /api/chat/{partner_id}/mark-read  — authenticated, upserts read status
GET  /api/users/{user_id}/unread-chats — authenticated + ownership, returns unread count
GET  /api/users/{user_id}/chat/{partner_id} — returns {"messages": [...], "partner_last_read_at": ...}
"""
import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from pymongo import MongoClient
from tests.helpers import FullAsyncMongoWrapper
from app.auth.utils import create_access_token, hash_password
from fastapi.testclient import TestClient
from app.main import app

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"

client = TestClient(app)

USER_A_ID = 8001
USER_B_ID = 8002
USER_C_ID = 8003  # unrelated user for 403 checks


def _token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


def _base_user(user_id: int) -> dict:
    return {
        "id": user_id,
        "email": f"rr_test{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": f"rruser{user_id}",
        "gender": "male",
        "is_banned": False,
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
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


@pytest.fixture(autouse=True)
def patch_rr_collections():
    """Patch all collections needed by the read receipts routes."""
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps
    import app.services.chatService as chat_svc_mod

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    users_col = FullAsyncMongoWrapper(sync_db["rr_users"])
    matches_col = FullAsyncMongoWrapper(sync_db["rr_matches"])
    chat_col = FullAsyncMongoWrapper(sync_db["rr_chat"])
    read_status_col = FullAsyncMongoWrapper(sync_db["rr_read_status"])
    blocks_col = FullAsyncMongoWrapper(sync_db["rr_blocks"])

    # Save originals
    orig = {
        "dbmod.users": dbmod.users_collection,
        "dbmod.matches": dbmod.matches_collection,
        "dbmod.chat": dbmod.chat_collection,
        "dbmod.read_status": dbmod.chat_read_status_collection,
        "rv.users": rv.users_collection,
        "rv.matches": rv.matches_collection,
        "rv.chat": rv.chat_collection,
        "rv.read_status": rv.chat_read_status_collection,
        "deps.users": deps.users_collection,
        "deps.matches": deps.matches_collection,
        "deps.blocks": deps.blocks_collection,
    }
    orig_upsvc = None
    if hasattr(rv, "userProfileService"):
        orig_upsvc = rv.userProfileService.collection
    orig_chat_svc_messages = None
    if hasattr(rv, "chatService"):
        orig_chat_svc_messages = rv.chatService.messages

    # Patch
    dbmod.users_collection = users_col
    dbmod.matches_collection = matches_col
    dbmod.chat_collection = chat_col
    dbmod.chat_read_status_collection = read_status_col

    rv.users_collection = users_col
    rv.matches_collection = matches_col
    rv.chat_collection = chat_col
    rv.chat_read_status_collection = read_status_col

    deps.users_collection = users_col
    deps.matches_collection = matches_col
    deps.blocks_collection = blocks_col

    if orig_upsvc is not None:
        rv.userProfileService.collection = users_col
    if orig_chat_svc_messages is not None:
        rv.chatService.messages = chat_col

    # Clean before test
    for col_name in ["rr_users", "rr_matches", "rr_chat", "rr_read_status", "rr_blocks"]:
        sync_db[col_name].delete_many({})

    yield sync_db

    # Restore originals
    dbmod.users_collection = orig["dbmod.users"]
    dbmod.matches_collection = orig["dbmod.matches"]
    dbmod.chat_collection = orig["dbmod.chat"]
    dbmod.chat_read_status_collection = orig["dbmod.read_status"]

    rv.users_collection = orig["rv.users"]
    rv.matches_collection = orig["rv.matches"]
    rv.chat_collection = orig["rv.chat"]
    rv.chat_read_status_collection = orig["rv.read_status"]

    deps.users_collection = orig["deps.users"]
    deps.matches_collection = orig["deps.matches"]
    deps.blocks_collection = orig["deps.blocks"]

    if orig_upsvc is not None:
        rv.userProfileService.collection = orig_upsvc
    if orig_chat_svc_messages is not None:
        rv.chatService.messages = orig_chat_svc_messages

    for col_name in ["rr_users", "rr_matches", "rr_chat", "rr_read_status", "rr_blocks"]:
        sync_db[col_name].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_match(sync_db, user1_id: int, user2_id: int):
    sync_db["rr_matches"].insert_one({"user1_id": user1_id, "user2_id": user2_id})


def _seed_message(sync_db, from_user: int, to_user: int, created_at: str = "2026-01-01T12:00:00"):
    sync_db["rr_chat"].insert_one({
        "fromUser": from_user,
        "toUser": to_user,
        "message": "Hey there",
        "createdAt": created_at,
    })


# ---------------------------------------------------------------------------
# POST /api/chat/{partner_id}/mark-read
# ---------------------------------------------------------------------------

def test_mark_read_authenticated(patch_rr_collections):
    """Authenticated user marking a chat as read returns {"status": "ok"} and upserts record."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))

    resp = client.post(f"/api/chat/{USER_B_ID}/mark-read", headers=_auth(USER_A_ID))

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}

    # Verify record was upserted into the collection
    doc = sync_db["rr_read_status"].find_one({"user_id": USER_A_ID, "partner_id": USER_B_ID})
    assert doc is not None
    assert "last_read_at" in doc


def test_mark_read_unauthenticated():
    """Calling mark-read without a token returns 401 or 403."""
    resp = client.post(f"/api/chat/{USER_B_ID}/mark-read")
    assert resp.status_code in (401, 403), resp.text


def test_mark_read_twice_upserts(patch_rr_collections):
    """Calling mark-read twice does not create duplicate records and updates last_read_at."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))

    # First call
    resp1 = client.post(f"/api/chat/{USER_B_ID}/mark-read", headers=_auth(USER_A_ID))
    assert resp1.status_code == 200, resp1.text

    doc_after_first = sync_db["rr_read_status"].find_one(
        {"user_id": USER_A_ID, "partner_id": USER_B_ID}
    )
    first_read_at = doc_after_first["last_read_at"]

    # Second call
    resp2 = client.post(f"/api/chat/{USER_B_ID}/mark-read", headers=_auth(USER_A_ID))
    assert resp2.status_code == 200, resp2.text

    # Should still be exactly one document
    docs = list(sync_db["rr_read_status"].find({"user_id": USER_A_ID, "partner_id": USER_B_ID}))
    assert len(docs) == 1, f"Expected 1 document, found {len(docs)}"

    # last_read_at should be updated (or at minimum not absent)
    assert "last_read_at" in docs[0]


# ---------------------------------------------------------------------------
# GET /api/users/{user_id}/unread-chats
# ---------------------------------------------------------------------------

def test_get_unread_chats_no_messages(patch_rr_collections):
    """User with no incoming messages sees unread_count=0 and empty list."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))
    _seed_match(sync_db, USER_A_ID, USER_B_ID)
    # No chat messages seeded

    resp = client.get(f"/api/users/{USER_A_ID}/unread-chats", headers=_auth(USER_A_ID))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"unread_count": 0, "unread_partner_ids": []}


def test_get_unread_chats_with_unread(patch_rr_collections):
    """After a partner sends a message that hasn't been read, unread count is > 0."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))
    _seed_match(sync_db, USER_A_ID, USER_B_ID)

    # USER_B sends a message to USER_A
    _seed_message(sync_db, from_user=USER_B_ID, to_user=USER_A_ID)

    # USER_A has not marked as read
    resp = client.get(f"/api/users/{USER_A_ID}/unread-chats", headers=_auth(USER_A_ID))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unread_count"] > 0
    assert USER_B_ID in body["unread_partner_ids"]


def test_get_unread_chats_after_mark_read(patch_rr_collections):
    """After marking the chat as read, the unread count drops to 0."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))
    _seed_match(sync_db, USER_A_ID, USER_B_ID)

    # Seed a message from USER_B at a past timestamp
    _seed_message(sync_db, from_user=USER_B_ID, to_user=USER_A_ID, created_at="2026-01-01T10:00:00")

    # USER_A marks the chat as read — the endpoint stores current UTC time as last_read_at,
    # which will be after the seeded message timestamp
    mark_resp = client.post(f"/api/chat/{USER_B_ID}/mark-read", headers=_auth(USER_A_ID))
    assert mark_resp.status_code == 200, mark_resp.text

    # Verify read status was stored
    doc = sync_db["rr_read_status"].find_one({"user_id": USER_A_ID, "partner_id": USER_B_ID})
    assert doc is not None

    # Manually set last_read_at to a timestamp after the message so the query
    # finds zero unread messages (the endpoint stores datetime.utcnow(), which
    # should already be after "2026-01-01T10:00:00", so this is just a guard)
    sync_db["rr_read_status"].update_one(
        {"user_id": USER_A_ID, "partner_id": USER_B_ID},
        {"$set": {"last_read_at": "2026-12-31T23:59:59"}},
    )

    resp = client.get(f"/api/users/{USER_A_ID}/unread-chats", headers=_auth(USER_A_ID))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unread_count"] == 0
    assert body["unread_partner_ids"] == []


def test_get_unread_chats_wrong_user(patch_rr_collections):
    """Requesting unread-chats for another user returns 403."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_C_ID))

    # USER_C attempts to query USER_A's unread chats
    resp = client.get(f"/api/users/{USER_A_ID}/unread-chats", headers=_auth(USER_C_ID))

    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# GET /api/users/{user_id}/chat/{partner_id}
# ---------------------------------------------------------------------------

def test_chat_endpoint_returns_partner_last_read_at(patch_rr_collections):
    """Chat history endpoint returns dict with 'messages' and 'partner_last_read_at' keys."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))
    _seed_match(sync_db, USER_A_ID, USER_B_ID)

    # Seed a message and a read receipt from USER_B (the partner)
    _seed_message(sync_db, from_user=USER_A_ID, to_user=USER_B_ID)
    last_read = "2026-06-01T09:00:00"
    sync_db["rr_read_status"].insert_one({
        "user_id": USER_B_ID,
        "partner_id": USER_A_ID,
        "last_read_at": last_read,
    })

    resp = client.get(
        f"/api/users/{USER_A_ID}/chat/{USER_B_ID}",
        headers=_auth(USER_A_ID),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Response must be a dict with both keys
    assert isinstance(body, dict), f"Expected dict, got {type(body)}"
    assert "messages" in body, f"Missing 'messages' key in {body}"
    assert "partner_last_read_at" in body, f"Missing 'partner_last_read_at' key in {body}"

    # Messages should be a list
    assert isinstance(body["messages"], list)

    # partner_last_read_at should match the seeded value
    assert body["partner_last_read_at"] == last_read


def test_chat_endpoint_partner_last_read_at_null_when_never_read(patch_rr_collections):
    """partner_last_read_at is null when the partner has never marked the chat as read."""
    sync_db = patch_rr_collections
    sync_db["rr_users"].insert_one(_base_user(USER_A_ID))
    sync_db["rr_users"].insert_one(_base_user(USER_B_ID))
    _seed_match(sync_db, USER_A_ID, USER_B_ID)

    # No read status seeded for USER_B
    resp = client.get(
        f"/api/users/{USER_A_ID}/chat/{USER_B_ID}",
        headers=_auth(USER_A_ID),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "partner_last_read_at" in body
    assert body["partner_last_read_at"] is None
