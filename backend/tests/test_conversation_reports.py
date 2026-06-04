"""
Tests for P3AD.4 — Reported Conversation Moderation.

POST /api/chat/{partner_id}/report                          — authenticated, rate-limited 5/hr
GET  /api/admin/conversation-reports                        — admin-only
GET  /api/admin/conversation-reports/{report_id}/messages   — admin-only
POST /api/admin/conversation-reports/{report_id}/resolve    — admin-only
"""
import os

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from bson import ObjectId
from pymongo import MongoClient
from tests.helpers import FullAsyncMongoWrapper
from app.auth.utils import create_access_token, hash_password
from fastapi.testclient import TestClient
from app.main import app

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"

client = TestClient(app)

ADMIN_USER_ID = 9001
REPORTER_USER_ID = 9002
REPORTED_USER_ID = 9003
UNMATCHED_USER_ID = 9004


def _token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


def _base_user(user_id: int, username: str = None) -> dict:
    return {
        "id": user_id,
        "email": f"crtest{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": username or f"cruser{user_id}",
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
def set_admin_env(monkeypatch):
    monkeypatch.setenv("ADMIN_USER_IDS", str(ADMIN_USER_ID))


@pytest.fixture(autouse=True)
def patch_cr_collections():
    """Patch conversation_reports, matches, chat, and users collections."""
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    users_col = FullAsyncMongoWrapper(sync_db["cr_users"])
    matches_col = FullAsyncMongoWrapper(sync_db["cr_matches"])
    chat_col = FullAsyncMongoWrapper(sync_db["cr_chat"])
    cr_col = FullAsyncMongoWrapper(sync_db["cr_conv_reports"])

    # Save originals
    orig = {
        "dbmod.users": dbmod.users_collection,
        "dbmod.matches": dbmod.matches_collection,
        "dbmod.chat": dbmod.chat_collection,
        "dbmod.cr": dbmod.conversation_reports_collection,
        "rv.users": rv.users_collection,
        "rv.matches": rv.matches_collection,
        "rv.chat": rv.chat_collection,
        "rv.cr": rv.conversation_reports_collection,
        "deps.users": deps.users_collection,
    }

    # Patch database module
    dbmod.users_collection = users_col
    dbmod.matches_collection = matches_col
    dbmod.chat_collection = chat_col
    dbmod.conversation_reports_collection = cr_col

    # Patch router-level references
    rv.users_collection = users_col
    rv.matches_collection = matches_col
    rv.chat_collection = chat_col
    rv.conversation_reports_collection = cr_col

    # Patch auth dependencies
    deps.users_collection = users_col

    # Patch userProfileService if it holds its own reference
    orig_upsvc = None
    if hasattr(rv, "userProfileService"):
        orig_upsvc = rv.userProfileService.collection
        rv.userProfileService.collection = users_col

    # Clean before test
    for col_name in ["cr_users", "cr_matches", "cr_chat", "cr_conv_reports"]:
        sync_db[col_name].delete_many({})

    yield sync_db

    # Restore originals
    dbmod.users_collection = orig["dbmod.users"]
    dbmod.matches_collection = orig["dbmod.matches"]
    dbmod.chat_collection = orig["dbmod.chat"]
    dbmod.conversation_reports_collection = orig["dbmod.cr"]
    rv.users_collection = orig["rv.users"]
    rv.matches_collection = orig["rv.matches"]
    rv.chat_collection = orig["rv.chat"]
    rv.conversation_reports_collection = orig["rv.cr"]
    deps.users_collection = orig["deps.users"]
    if orig_upsvc is not None:
        rv.userProfileService.collection = orig_upsvc

    for col_name in ["cr_users", "cr_matches", "cr_chat", "cr_conv_reports"]:
        sync_db[col_name].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_match(sync_db, user1_id: int, user2_id: int):
    sync_db["cr_matches"].insert_one({
        "user1_id": user1_id,
        "user2_id": user2_id,
    })


def _seed_report(sync_db, reporter_id: int, reported_id: int,
                 reason: str = "harassment", status: str = "pending") -> str:
    result = sync_db["cr_conv_reports"].insert_one({
        "reporter_id": reporter_id,
        "reported_user_id": reported_id,
        "reason": reason,
        "status": status,
        "createdAt": "2026-01-01T00:00:00",
    })
    return str(result.inserted_id)


# ---------------------------------------------------------------------------
# POST /api/chat/{partner_id}/report
# ---------------------------------------------------------------------------

def test_report_conversation_authenticated(patch_cr_collections):
    """Matched users can report a conversation — returns 200 {"status": "ok"}."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID, "reporter"))
    sync_db["cr_users"].insert_one(_base_user(REPORTED_USER_ID, "reported"))
    _seed_match(sync_db, REPORTER_USER_ID, REPORTED_USER_ID)

    resp = client.post(
        f"/api/chat/{REPORTED_USER_ID}/report",
        json={"reason": "This user sent threatening messages"},
        headers=_auth(REPORTER_USER_ID),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}

    # Verify report was persisted
    doc = sync_db["cr_conv_reports"].find_one({"reporter_id": REPORTER_USER_ID})
    assert doc is not None
    assert doc["reported_user_id"] == REPORTED_USER_ID
    assert doc["status"] == "pending"


def test_report_conversation_unauthenticated():
    """No auth token returns 401 or 403 (HTTPBearer raises 403 by default)."""
    resp = client.post(
        f"/api/chat/{REPORTED_USER_ID}/report",
        json={"reason": "No auth test"},
    )
    assert resp.status_code in (401, 403), resp.text


def test_report_conversation_not_matched(patch_cr_collections):
    """Users who are not matched cannot report each other — returns 403."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID))
    sync_db["cr_users"].insert_one(_base_user(UNMATCHED_USER_ID))
    # No match document seeded

    resp = client.post(
        f"/api/chat/{UNMATCHED_USER_ID}/report",
        json={"reason": "Spam messages"},
        headers=_auth(REPORTER_USER_ID),
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# GET /api/admin/conversation-reports
# ---------------------------------------------------------------------------

def test_admin_get_conversation_reports(patch_cr_collections):
    """Admin sees list of pending conversation reports with reporter/reported usernames."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID, "reporter"))
    sync_db["cr_users"].insert_one(_base_user(REPORTED_USER_ID, "reported"))
    _seed_report(sync_db, REPORTER_USER_ID, REPORTED_USER_ID, "harassment", "pending")

    resp = client.get("/api/admin/conversation-reports", headers=_auth(ADMIN_USER_ID))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "reports" in body
    assert isinstance(body["reports"], list)
    assert len(body["reports"]) >= 1

    # Verify the entry includes joined usernames
    entry = body["reports"][0]
    assert "reporter_username" in entry
    assert "reported_username" in entry
    assert entry["reporter_username"] == "reporter"
    assert entry["reported_username"] == "reported"


def test_admin_get_conversation_reports_non_admin(patch_cr_collections):
    """Regular user cannot access admin conversation-reports endpoint — 403."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID))

    resp = client.get("/api/admin/conversation-reports", headers=_auth(REPORTER_USER_ID))
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# POST /api/admin/conversation-reports/{report_id}/resolve
# ---------------------------------------------------------------------------

def test_admin_resolve_report_dismiss(patch_cr_collections):
    """Admin can dismiss a report — status set to 'resolved', reported user not banned."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID))
    sync_db["cr_users"].insert_one(_base_user(REPORTED_USER_ID))
    report_id = _seed_report(sync_db, REPORTER_USER_ID, REPORTED_USER_ID)

    resp = client.post(
        f"/api/admin/conversation-reports/{report_id}/resolve",
        json={"action": "dismiss"},
        headers=_auth(ADMIN_USER_ID),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}

    # Verify report is resolved
    doc = sync_db["cr_conv_reports"].find_one({"_id": ObjectId(report_id)})
    assert doc["status"] == "resolved"

    # Verify reported user is NOT banned
    reported = sync_db["cr_users"].find_one({"id": REPORTED_USER_ID})
    assert reported.get("is_banned") is False


def test_admin_resolve_report_ban(patch_cr_collections):
    """Admin can ban reported user — status set to 'resolved' and reported user is banned."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID))
    sync_db["cr_users"].insert_one(_base_user(REPORTED_USER_ID))
    report_id = _seed_report(sync_db, REPORTER_USER_ID, REPORTED_USER_ID)

    resp = client.post(
        f"/api/admin/conversation-reports/{report_id}/resolve",
        json={"action": "ban"},
        headers=_auth(ADMIN_USER_ID),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}

    # Verify report is resolved
    doc = sync_db["cr_conv_reports"].find_one({"_id": ObjectId(report_id)})
    assert doc["status"] == "resolved"

    # Verify reported user IS banned
    reported = sync_db["cr_users"].find_one({"id": REPORTED_USER_ID})
    assert reported.get("is_banned") is True


def test_admin_resolve_nonexistent_report(patch_cr_collections):
    """Resolving a report that does not exist returns 404."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))

    fake_id = str(ObjectId())
    resp = client.post(
        f"/api/admin/conversation-reports/{fake_id}/resolve",
        json={"action": "dismiss"},
        headers=_auth(ADMIN_USER_ID),
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# GET /api/admin/conversation-reports/{report_id}/messages
# ---------------------------------------------------------------------------

def test_admin_get_report_messages(patch_cr_collections):
    """Admin can fetch the full chat history for a reported conversation."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID, "reporter"))
    sync_db["cr_users"].insert_one(_base_user(REPORTED_USER_ID, "reported"))

    report_id = _seed_report(sync_db, REPORTER_USER_ID, REPORTED_USER_ID)

    # Seed some chat messages between the two users
    sync_db["cr_chat"].insert_many([
        {
            "fromUser": REPORTER_USER_ID,
            "toUser": REPORTED_USER_ID,
            "message": "Hello",
            "createdAt": "2026-01-01T10:00:00",
        },
        {
            "fromUser": REPORTED_USER_ID,
            "toUser": REPORTER_USER_ID,
            "message": "Stop messaging me",
            "createdAt": "2026-01-01T10:01:00",
        },
    ])

    resp = client.get(
        f"/api/admin/conversation-reports/{report_id}/messages",
        headers=_auth(ADMIN_USER_ID),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "messages" in body
    assert isinstance(body["messages"], list)
    assert len(body["messages"]) == 2

    texts = [m["message"] for m in body["messages"]]
    assert "Hello" in texts
    assert "Stop messaging me" in texts


def test_admin_get_report_messages_not_found(patch_cr_collections):
    """Getting messages for a non-existent report_id returns 404."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))

    fake_id = str(ObjectId())
    resp = client.get(
        f"/api/admin/conversation-reports/{fake_id}/messages",
        headers=_auth(ADMIN_USER_ID),
    )
    assert resp.status_code == 404, resp.text


def test_admin_get_report_messages_non_admin(patch_cr_collections):
    """Regular user cannot access admin messages endpoint — 403."""
    sync_db = patch_cr_collections
    sync_db["cr_users"].insert_one(_base_user(REPORTER_USER_ID))
    report_id = _seed_report(sync_db, REPORTER_USER_ID, REPORTED_USER_ID)

    resp = client.get(
        f"/api/admin/conversation-reports/{report_id}/messages",
        headers=_auth(REPORTER_USER_ID),
    )
    assert resp.status_code == 403, resp.text
