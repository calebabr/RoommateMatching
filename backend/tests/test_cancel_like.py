"""
Tests for P2.29 — Cancel Like endpoint.

Expected endpoint: DELETE /api/users/{user_id}/like/{target_id}

Scenarios:
  1. test_cancel_like_success          — user cancels their own pending like → 200/204
  2. test_cancel_like_not_found        — cancelling a non-existent like → 404
  3. test_cancel_like_after_match      — cancelling a like that produced a match → 409
  4. test_cancel_like_wrong_user       — user A cannot cancel user B's like → 403
  5. test_cancel_like_unauthenticated  — no token → 401/403
"""

import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from app.main import app
from app.auth.utils import create_access_token, hash_password

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"

client = TestClient(app)


def _make_token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_cancel_like_collections():
    """Patch all collections needed by cancel-like and the like routes."""
    from tests.helpers import FullAsyncMongoWrapper
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    likes_col = FullAsyncMongoWrapper(sync_db["likes"])
    matches_col = FullAsyncMongoWrapper(sync_db["matches"])

    orig = {
        "dbmod.likes_collection": dbmod.likes_collection,
        "dbmod.matches_collection": dbmod.matches_collection,
        "deps.matches_collection": deps.matches_collection,
        "rv.likeService.likes": rv.likeService.likes,
        "rv.likeService.matches": rv.likeService.matches,
        "rv.likeService.users": rv.likeService.users,
    }

    dbmod.likes_collection = likes_col
    dbmod.matches_collection = matches_col
    deps.matches_collection = matches_col
    rv.likeService.likes = likes_col
    rv.likeService.matches = matches_col
    rv.likeService.users = dbmod.users_collection

    for col in ["likes", "matches"]:
        sync_db[col].delete_many({})

    yield

    dbmod.likes_collection = orig["dbmod.likes_collection"]
    dbmod.matches_collection = orig["dbmod.matches_collection"]
    deps.matches_collection = orig["deps.matches_collection"]
    rv.likeService.likes = orig["rv.likeService.likes"]
    rv.likeService.matches = orig["rv.likeService.matches"]
    rv.likeService.users = orig["rv.likeService.users"]

    for col in ["likes", "matches"]:
        sync_db[col].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(sync_db, user_id: int, matched_with: list = None) -> dict:
    doc = {
        "id": user_id,
        "email": f"cl{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": f"canceluser{user_id}",
        "gender": "male",
        "matched": False,
        "matchCount": 0,
        "matchedWith": matched_with or [],
        "bio": "",
        "photoUrl": "",
        "lifestyleTags": [],
        "sleepScoreWD": {"value": 8.0, "isDealBreaker": False},
        "sleepScoreWE": {"value": 10.0, "isDealBreaker": False},
        "cleanlinessScore": {"value": 5.0, "isDealBreaker": False},
        "noiseToleranceScore": {"value": 5.0, "isDealBreaker": False},
        "guestsScore": {"value": 5.0, "isDealBreaker": False},
        "personalityScore": {"value": 5.0, "isDealBreaker": False},
        "smokingScore": {"value": 0.0, "isDealBreaker": False},
        "sharedSpaceScore": {"value": 5.0, "isDealBreaker": False},
        "communicationScore": {"value": 5.0, "isDealBreaker": False},
    }
    sync_db["users"].insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCancelLike:
    """DELETE /api/users/{user_id}/like/{target_id}"""

    def test_cancel_like_success(self):
        """User A can cancel a pending like they sent to user B.

        After cancellation the like document no longer exists, and a subsequent
        GET of A's likes-sent should not include B.
        """
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 1001)
        _insert_user(sync_db, 1002)

        # A likes B
        sync_db["likes"].insert_one({"fromUser": 1001, "toUser": 1002})

        resp = client.delete("/api/users/1001/like/1002", headers=_auth(1001))
        assert resp.status_code in (200, 204), (
            f"Expected 200/204, got {resp.status_code}: {resp.text}"
        )

        # Like should no longer exist
        remaining = sync_db["likes"].count_documents({"fromUser": 1001, "toUser": 1002})
        assert remaining == 0, "Like document should be removed after cancellation"

    def test_cancel_like_not_found(self):
        """Cancelling a like that does not exist returns 404."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 1101)
        _insert_user(sync_db, 1102)

        # No like inserted
        resp = client.delete("/api/users/1101/like/1102", headers=_auth(1101))
        assert resp.status_code == 404, (
            f"Expected 404 for non-existent like, got {resp.status_code}: {resp.text}"
        )

    def test_cancel_like_after_match(self):
        """Cancelling a like that already resulted in a match should return 409.

        Once a mutual like becomes a match, the underlying like docs are deleted
        by the match-creation flow. The cancel endpoint should detect the match
        exists and refuse with 409 Conflict.
        """
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 1201, matched_with=[1202])
        _insert_user(sync_db, 1202, matched_with=[1201])

        # Simulate matched state — likes were cleaned up, match document exists
        sync_db["matches"].insert_one({
            "user1_id": 1201,
            "user2_id": 1202,
            "confirmedAt": None,
        })

        resp = client.delete("/api/users/1201/like/1202", headers=_auth(1201))
        assert resp.status_code == 409, (
            f"Expected 409 (already matched), got {resp.status_code}: {resp.text}"
        )

    def test_cancel_like_wrong_user(self):
        """User A cannot cancel user B's like (A does not own it) → 403."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 1301)
        _insert_user(sync_db, 1302)
        _insert_user(sync_db, 1303)

        # B liked C
        sync_db["likes"].insert_one({"fromUser": 1302, "toUser": 1303})

        # A tries to cancel B's like — should fail with 403
        resp = client.delete("/api/users/1302/like/1303", headers=_auth(1301))
        assert resp.status_code == 403, (
            f"Expected 403, got {resp.status_code}: {resp.text}"
        )

    def test_cancel_like_unauthenticated(self):
        """No token → 401 or 403."""
        resp = client.delete("/api/users/1401/like/1402")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403, got {resp.status_code}"
        )
