"""
Tests for P3AD.2 — User Feedback endpoints.

POST /api/feedback      — authenticated, rate-limited 10/hr
GET  /api/admin/feedback — admin-only
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

ADMIN_USER_ID = 8001
REGULAR_USER_ID = 8002


def _token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


def _base_user(user_id: int, username: str = None) -> dict:
    return {
        "id": user_id,
        "email": f"fbtest{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": username or f"fbuser{user_id}",
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
def patch_feedback_collections():
    """Patch feedback_collection and users_collection used by feedback routes."""
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    feedback_col = FullAsyncMongoWrapper(sync_db["fb_feedback"])
    users_col = FullAsyncMongoWrapper(sync_db["fb_users"])

    # Save originals
    orig_feedback_db = dbmod.feedback_collection
    orig_feedback_rv = rv.feedback_collection
    orig_users_db = dbmod.users_collection
    orig_users_rv = rv.users_collection
    orig_users_deps = deps.users_collection

    # Patch
    dbmod.feedback_collection = feedback_col
    rv.feedback_collection = feedback_col
    dbmod.users_collection = users_col
    rv.users_collection = users_col
    deps.users_collection = users_col

    # Also patch any service that holds a reference to users_collection
    if hasattr(rv, "userProfileService"):
        orig_upsvc = rv.userProfileService.collection
        rv.userProfileService.collection = users_col
    else:
        orig_upsvc = None

    # Clean before test
    sync_db["fb_feedback"].delete_many({})
    sync_db["fb_users"].delete_many({})

    yield sync_db

    # Restore originals
    dbmod.feedback_collection = orig_feedback_db
    rv.feedback_collection = orig_feedback_rv
    dbmod.users_collection = orig_users_db
    rv.users_collection = orig_users_rv
    deps.users_collection = orig_users_deps
    if orig_upsvc is not None:
        rv.userProfileService.collection = orig_upsvc

    sync_db["fb_feedback"].delete_many({})
    sync_db["fb_users"].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# POST /api/feedback
# ---------------------------------------------------------------------------

def test_submit_feedback_authenticated(patch_feedback_collections):
    """Authenticated user can submit feedback — returns 200 {"status": "ok"}."""
    sync_db = patch_feedback_collections
    sync_db["fb_users"].insert_one(_base_user(REGULAR_USER_ID, "regularuser"))

    resp = client.post(
        "/api/feedback",
        json={"message": "Great app!"},
        headers=_auth(REGULAR_USER_ID),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}

    # Verify persisted in DB
    doc = sync_db["fb_feedback"].find_one({"user_id": REGULAR_USER_ID})
    assert doc is not None
    assert doc["message"] == "Great app!"


def test_submit_feedback_unauthenticated():
    """No auth token returns 401 or 403 (HTTPBearer raises 403 by default)."""
    resp = client.post(
        "/api/feedback",
        json={"message": "No auth"},
    )
    assert resp.status_code in (401, 403), resp.text


def test_submit_feedback_empty_message(patch_feedback_collections):
    """Empty message string fails Pydantic validation — 422."""
    sync_db = patch_feedback_collections
    sync_db["fb_users"].insert_one(_base_user(REGULAR_USER_ID))

    resp = client.post(
        "/api/feedback",
        json={"message": ""},
        headers=_auth(REGULAR_USER_ID),
    )
    assert resp.status_code == 422, resp.text


def test_submit_feedback_too_long(patch_feedback_collections):
    """Message exceeding 2000 characters fails Pydantic validation — 422."""
    sync_db = patch_feedback_collections
    sync_db["fb_users"].insert_one(_base_user(REGULAR_USER_ID))

    resp = client.post(
        "/api/feedback",
        json={"message": "x" * 2001},
        headers=_auth(REGULAR_USER_ID),
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# GET /api/admin/feedback
# ---------------------------------------------------------------------------

def test_admin_get_feedback_returns_list(patch_feedback_collections):
    """Admin can fetch feedback list; includes the submitted entry with username."""
    sync_db = patch_feedback_collections
    sync_db["fb_users"].insert_one(_base_user(ADMIN_USER_ID, "adminuser"))
    sync_db["fb_users"].insert_one(_base_user(REGULAR_USER_ID, "regularuser"))

    # Seed a feedback document directly
    sync_db["fb_feedback"].insert_one({
        "user_id": REGULAR_USER_ID,
        "message": "Needs dark mode",
        "createdAt": "2026-01-01T00:00:00",
    })

    resp = client.get("/api/admin/feedback", headers=_auth(ADMIN_USER_ID))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "feedback" in body
    assert isinstance(body["feedback"], list)
    assert len(body["feedback"]) >= 1
    # Check that the submitted entry is present with a username
    entry = next((f for f in body["feedback"] if f.get("message") == "Needs dark mode"), None)
    assert entry is not None
    assert entry.get("username") == "regularuser"


def test_admin_get_feedback_non_admin_forbidden(patch_feedback_collections):
    """Regular user cannot access admin feedback endpoint — 403."""
    sync_db = patch_feedback_collections
    sync_db["fb_users"].insert_one(_base_user(REGULAR_USER_ID))

    resp = client.get("/api/admin/feedback", headers=_auth(REGULAR_USER_ID))
    assert resp.status_code == 403, resp.text
