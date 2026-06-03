"""Tests for the block system: block/unblock endpoints, auto-unmatch, and filtering."""
import json
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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_block_collections():
    """Patch all collections needed by BlockService and the block/unblock routes.

    Saves originals and restores them on teardown to prevent cross-module pollution.
    """
    from tests.helpers import FullAsyncMongoWrapper
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    blocks_col = FullAsyncMongoWrapper(sync_db["blocks"])
    likes_col = FullAsyncMongoWrapper(sync_db["likes"])
    matches_col = FullAsyncMongoWrapper(sync_db["matches"])

    # Save originals
    orig = {
        "dbmod.blocks_collection": dbmod.blocks_collection,
        "dbmod.likes_collection": dbmod.likes_collection,
        "dbmod.matches_collection": dbmod.matches_collection,
        "deps.blocks_collection": deps.blocks_collection,
        "deps.matches_collection": deps.matches_collection,
        "rv.blockService.blocks": rv.blockService.blocks,
        "rv.blockService.likes": rv.blockService.likes,
        "rv.blockService.matches": rv.blockService.matches,
        "rv.blockService.users": rv.blockService.users,
        "rv.likeService.likes": rv.likeService.likes,
        "rv.likeService.matches": rv.likeService.matches,
        "rv.likeService.users": rv.likeService.users,
    }

    # Patch module-level globals
    dbmod.blocks_collection = blocks_col
    dbmod.likes_collection = likes_col
    dbmod.matches_collection = matches_col
    deps.blocks_collection = blocks_col
    deps.matches_collection = matches_col

    # Patch BlockService instance attached to the router
    rv.blockService.blocks = blocks_col
    rv.blockService.likes = likes_col
    rv.blockService.matches = matches_col
    rv.blockService.users = dbmod.users_collection

    # Patch LikeService so get_likes_received works correctly
    rv.likeService.likes = likes_col
    rv.likeService.matches = matches_col
    rv.likeService.users = dbmod.users_collection

    # Clean before each test
    for col in ["blocks", "likes", "matches"]:
        sync_db[col].delete_many({})

    yield

    # Restore originals
    dbmod.blocks_collection = orig["dbmod.blocks_collection"]
    dbmod.likes_collection = orig["dbmod.likes_collection"]
    dbmod.matches_collection = orig["dbmod.matches_collection"]
    deps.blocks_collection = orig["deps.blocks_collection"]
    deps.matches_collection = orig["deps.matches_collection"]
    rv.blockService.blocks = orig["rv.blockService.blocks"]
    rv.blockService.likes = orig["rv.blockService.likes"]
    rv.blockService.matches = orig["rv.blockService.matches"]
    rv.blockService.users = orig["rv.blockService.users"]
    rv.likeService.likes = orig["rv.likeService.likes"]
    rv.likeService.matches = orig["rv.likeService.matches"]
    rv.likeService.users = orig["rv.likeService.users"]

    for col in ["blocks", "likes", "matches"]:
        sync_db[col].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(sync_db, user_id: int, username: str = None, matched_with: list = None) -> dict:
    doc = {
        "id": user_id,
        "email": f"blk{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": username or f"blkuser{user_id}",
        "gender": "male",
        "matched": False,
        "matchCount": 0,
        "matchedWith": matched_with or [],
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
    sync_db["users"].insert_one(doc)
    return doc


def _insert_match(sync_db, user1_id: int, user2_id: int):
    sync_db["matches"].insert_one({
        "user1_id": user1_id,
        "user2_id": user2_id,
        "compatibilityScore": 0.9,
        "confirmedAt": None,
    })


# ---------------------------------------------------------------------------
# Tests — Block and Unblock
# ---------------------------------------------------------------------------

class TestBlockUser:
    """POST /api/users/{user_id}/block and POST /api/users/{user_id}/unblock"""

    def test_block_user_success_200(self):
        """Blocking another user returns 200."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 101)
        _insert_user(sync_db, 102)

        resp = client.post(
            "/api/users/101/block",
            json={"userId": 102},
            headers=_auth(101),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "User blocked"

    def test_block_auto_unmatches_pair(self):
        """After blocking, the match document is removed and matchedWith is updated on both users."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 201, matched_with=[202])
        _insert_user(sync_db, 202, matched_with=[201])
        sync_db["users"].update_one({"id": 201}, {"$set": {"matched": True, "matchCount": 1}})
        sync_db["users"].update_one({"id": 202}, {"$set": {"matched": True, "matchCount": 1}})
        _insert_match(sync_db, 201, 202)

        resp = client.post(
            "/api/users/201/block",
            json={"userId": 202},
            headers=_auth(201),
        )
        assert resp.status_code == 200

        # Match record must be gone
        remaining = list(sync_db["matches"].find({
            "$or": [
                {"user1_id": 201, "user2_id": 202},
                {"user1_id": 202, "user2_id": 201},
            ]
        }))
        assert len(remaining) == 0

        # matchedWith updated on both users
        u201 = sync_db["users"].find_one({"id": 201})
        u202 = sync_db["users"].find_one({"id": 202})
        assert 202 not in (u201.get("matchedWith") or [])
        assert 201 not in (u202.get("matchedWith") or [])

    def test_unblock_user_success_200(self):
        """Unblocking a user returns 200 and removes the block record."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 301)
        _insert_user(sync_db, 302)

        # Block first
        client.post("/api/users/301/block", json={"userId": 302}, headers=_auth(301))
        assert sync_db["blocks"].count_documents({"blockerId": 301, "blockedId": 302}) == 1

        # Unblock
        resp = client.post(
            "/api/users/301/unblock",
            json={"userId": 302},
            headers=_auth(301),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "User unblocked"
        assert sync_db["blocks"].count_documents({"blockerId": 301, "blockedId": 302}) == 0

    def test_cannot_block_yourself_400(self):
        """Blocking your own user ID returns 400."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 401)

        resp = client.post(
            "/api/users/401/block",
            json={"userId": 401},
            headers=_auth(401),
        )
        assert resp.status_code == 400

    def test_unauthenticated_block_returns_401_or_403(self):
        """Attempting to block without a token returns 401/403."""
        resp = client.post("/api/users/501/block", json={"userId": 502})
        assert resp.status_code in (401, 403)

    def test_block_idempotent(self):
        """Blocking the same user twice doesn't error and produces only one block record."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 601)
        _insert_user(sync_db, 602)

        client.post("/api/users/601/block", json={"userId": 602}, headers=_auth(601))
        resp2 = client.post("/api/users/601/block", json={"userId": 602}, headers=_auth(601))
        assert resp2.status_code == 200

        count = sync_db["blocks"].count_documents({"blockerId": 601, "blockedId": 602})
        assert count == 1


# ---------------------------------------------------------------------------
# Tests — Block filtering
# ---------------------------------------------------------------------------

class TestBlockFiltering:
    """Blocked users should not appear in discover/recommendations or likes."""

    def test_blocked_user_absent_from_top_matches(self):
        """Top-matches endpoint filters out users blocked by the requester."""
        from tests.helpers import FullAsyncMongoWrapper
        import app.routers.userRoutes as rv

        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 701)
        _insert_user(sync_db, 702)

        # Insert a fake recommendation for user 701 pointing at 702
        sync_db["recommendations"].delete_many({})
        sync_db["recommendations"].insert_one({
            "userId": 701,
            "matches": [{"user_id": 702, "compatibilityScore": 0.95}],
        })
        rv.recommendationService.collection = FullAsyncMongoWrapper(sync_db["recommendations"])

        # Block user 702
        client.post("/api/users/701/block", json={"userId": 702}, headers=_auth(701))

        resp = client.get("/api/users/701/top-matches", headers=_auth(701))
        if resp.status_code == 200:
            ids_returned = [m["user_id"] for m in resp.json().get("matches", [])]
            assert 702 not in ids_returned
        else:
            assert resp.status_code == 404

        sync_db["recommendations"].delete_many({})

    def test_block_is_bidirectional_in_filtering(self):
        """A blocks B: A's likes-received endpoint does not show B (B is blocked)."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 801)
        _insert_user(sync_db, 802)

        # 802 liked 801
        sync_db["likes"].insert_one({"fromUser": 802, "toUser": 801})

        # 801 blocks 802
        client.post("/api/users/801/block", json={"userId": 802}, headers=_auth(801))

        # 801's likes-received should not include 802 (blocked)
        resp = client.get("/api/users/801/likes-received", headers=_auth(801))
        assert resp.status_code == 200
        from_users = [like.get("fromUser") for like in resp.json()]
        assert 802 not in from_users


# ---------------------------------------------------------------------------
# Tests — Chat blocked
# ---------------------------------------------------------------------------

class TestBlockChat:
    """Blocked users cannot send chat messages to each other."""

    def test_cannot_send_chat_to_blocked_user_403(self):
        """verify_match_exists dependency raises 403 when a block exists between the pair."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 901)
        _insert_user(sync_db, 902)

        # They are matched
        _insert_match(sync_db, 901, 902)
        sync_db["users"].update_one({"id": 901}, {"$set": {"matched": True, "matchedWith": [902], "matchCount": 1}})
        sync_db["users"].update_one({"id": 902}, {"$set": {"matched": True, "matchedWith": [901], "matchCount": 1}})

        # 901 blocks 902
        client.post("/api/users/901/block", json={"userId": 902}, headers=_auth(901))

        # 901 tries to send a message — 403 because block check fires before match check
        resp = client.post(
            "/api/users/901/chat/902",
            json={"content": "hello"},
            headers=_auth(901),
        )
        assert resp.status_code == 403
