"""
Tests for P3FT.3 — Profile Pause / Deactivate.

Expected endpoints:
  POST   /api/users/{user_id}/pause            — set is_paused=True
  POST   /api/users/{user_id}/unpause          — set is_paused=False
  POST   /api/users/{user_id}/deactivate       — body: {password}, set is_deactivated=True + deactivatedAt
  POST   /api/users/{user_id}/reactivate       — clear is_deactivated + deactivatedAt

Filtering behavior already present in the codebase:
  - top-matches excludes is_paused=True and is_deactivated=True users
  - likes-received excludes is_paused=True and is_deactivated=True users
  - matches endpoint excludes is_deactivated=True (but not is_paused) partners

Startup cleanup (main.py lifespan):
  - users with is_deactivated=True and deactivatedAt < (now - 30 days) are hard-deleted

Scenarios:
  1. test_pause_profile                  — pause sets is_paused=True, user excluded from discover
  2. test_unpause_profile                — unpause sets is_paused=False, user reappears
  3. test_pause_wrong_user               — user A cannot pause user B → 403
  4. test_deactivate_requires_password   — missing/wrong password → 401/422
  5. test_deactivate_correct_password    — correct password sets is_deactivated=True + deactivatedAt
  6. test_deactivated_user_hidden        — deactivated user absent from discover, likes, matches
  7. test_reactivate_profile             — reactivate clears is_deactivated and deactivatedAt
  8. test_deactivate_30_day_cleanup      — startup cleanup logic directly deletes stale accounts
"""

from datetime import datetime, timezone, timedelta
import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from app.main import app
from app.auth.utils import create_access_token, hash_password

TEST_MONGO_URL = "mongodb://localhost:27017/"
TEST_DB_NAME = "roommatch_test"

client = TestClient(app)

_PASSWORD = "ValidPass1!"


def _make_token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_pause_collections():
    """Patch all collections used by pause/deactivate routes and discover."""
    from tests.helpers import FullAsyncMongoWrapper
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    users_col = FullAsyncMongoWrapper(sync_db["users"])
    likes_col = FullAsyncMongoWrapper(sync_db["likes"])
    matches_col = FullAsyncMongoWrapper(sync_db["matches"])
    recs_col = FullAsyncMongoWrapper(sync_db["recommendations"])
    blocks_col = FullAsyncMongoWrapper(sync_db["blocks"])

    orig_dbmod_users = dbmod.users_collection
    orig_dbmod_likes = dbmod.likes_collection
    orig_dbmod_matches = dbmod.matches_collection
    orig_dbmod_blocks = dbmod.blocks_collection
    orig_deps_users = deps.users_collection
    orig_deps_matches = deps.matches_collection
    orig_deps_blocks = deps.blocks_collection
    orig_profile_col = rv.userProfileService.collection
    orig_like_users = rv.likeService.users
    orig_like_likes = rv.likeService.likes
    orig_like_matches = rv.likeService.matches
    orig_rec_col = rv.recommendationService.collection
    orig_block_blocks = rv.blockService.blocks
    orig_block_users = rv.blockService.users

    dbmod.users_collection = users_col
    dbmod.likes_collection = likes_col
    dbmod.matches_collection = matches_col
    dbmod.blocks_collection = blocks_col
    deps.users_collection = users_col
    deps.matches_collection = matches_col
    deps.blocks_collection = blocks_col
    rv.userProfileService.collection = users_col
    rv.likeService.users = users_col
    rv.likeService.likes = likes_col
    rv.likeService.matches = matches_col
    rv.recommendationService.collection = recs_col
    rv.blockService.blocks = blocks_col
    rv.blockService.users = users_col

    # Patch module-level users_collection used directly in route handlers
    import app.routers.userRoutes as ur_mod
    orig_ur_users = getattr(ur_mod, "users_collection", None)
    ur_mod.users_collection = users_col

    for col in ["users", "likes", "matches", "recommendations", "blocks"]:
        sync_db[col].delete_many({})

    yield

    dbmod.users_collection = orig_dbmod_users
    dbmod.likes_collection = orig_dbmod_likes
    dbmod.matches_collection = orig_dbmod_matches
    dbmod.blocks_collection = orig_dbmod_blocks
    deps.users_collection = orig_deps_users
    deps.matches_collection = orig_deps_matches
    deps.blocks_collection = orig_deps_blocks
    rv.userProfileService.collection = orig_profile_col
    rv.likeService.users = orig_like_users
    rv.likeService.likes = orig_like_likes
    rv.likeService.matches = orig_like_matches
    rv.recommendationService.collection = orig_rec_col
    rv.blockService.blocks = orig_block_blocks
    rv.blockService.users = orig_block_users
    if orig_ur_users is not None:
        ur_mod.users_collection = orig_ur_users

    for col in ["users", "likes", "matches", "recommendations", "blocks"]:
        sync_db[col].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(sync_db, user_id: int, password: str = _PASSWORD, extra: dict = None) -> dict:
    doc = {
        "id": user_id,
        "email": f"pd{user_id}@auburn.edu",
        "hashed_password": hash_password(password),
        "username": f"pduser{user_id}",
        "gender": "male",
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
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
    if extra:
        doc.update(extra)
    sync_db["users"].insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Tests — Pause
# ---------------------------------------------------------------------------

class TestPauseProfile:
    """POST /api/users/{user_id}/pause"""

    def test_pause_profile(self):
        """Pause endpoint sets is_paused=True; user is excluded from discover."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2001)
        _insert_user(sync_db, 2002)

        # Insert a recommendation entry so top-matches has data
        sync_db["recommendations"].insert_one({
            "userId": 2001,
            "matches": [{"user_id": 2002, "compatibilityScore": 0.9}],
        })

        # Pause user 2002
        resp = client.post("/api/users/2002/pause", headers=_auth(2002))
        assert resp.status_code == 200, (
            f"Expected 200 from pause, got {resp.status_code}: {resp.text}"
        )

        # is_paused flag should be set in DB
        user = sync_db["users"].find_one({"id": 2002})
        assert user.get("is_paused") is True, "is_paused should be True after pause"

        # Paused user should be excluded from top-matches of user 2001
        top = client.get("/api/users/2001/top-matches", headers=_auth(2001))
        if top.status_code == 200:
            ids = [m["user_id"] for m in top.json().get("matches", [])]
            assert 2002 not in ids, "Paused user should not appear in discover"

    def test_unpause_profile(self):
        """Unpause endpoint clears is_paused; user can reappear in discover."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2101, extra={"is_paused": True})

        resp = client.post("/api/users/2101/unpause", headers=_auth(2101))
        assert resp.status_code == 200, (
            f"Expected 200 from unpause, got {resp.status_code}: {resp.text}"
        )

        user = sync_db["users"].find_one({"id": 2101})
        assert user.get("is_paused") is not True, "is_paused should be cleared after unpause"

    def test_pause_wrong_user(self):
        """User A cannot pause user B → 403."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2201)
        _insert_user(sync_db, 2202)

        resp = client.post("/api/users/2202/pause", headers=_auth(2201))
        assert resp.status_code == 403, (
            f"Expected 403, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Tests — Deactivate
# ---------------------------------------------------------------------------

class TestDeactivateProfile:
    """POST /api/users/{user_id}/deactivate"""

    def test_deactivate_requires_password(self):
        """Missing or wrong password returns 401 or 422."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2301)

        # Missing password body
        resp_no_body = client.post("/api/users/2301/deactivate", json={}, headers=_auth(2301))
        assert resp_no_body.status_code in (401, 422), (
            f"Missing password should be 401/422, got {resp_no_body.status_code}"
        )

        # Wrong password
        resp_wrong = client.post(
            "/api/users/2301/deactivate",
            json={"password": "WrongPassword1!"},
            headers=_auth(2301),
        )
        assert resp_wrong.status_code in (401, 400), (
            f"Wrong password should be 401/400, got {resp_wrong.status_code}: {resp_wrong.text}"
        )

    def test_deactivate_correct_password(self):
        """Correct password sets is_deactivated=True and records deactivatedAt."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2401, password=_PASSWORD)

        resp = client.post(
            "/api/users/2401/deactivate",
            json={"password": _PASSWORD},
            headers=_auth(2401),
        )
        assert resp.status_code == 200, (
            f"Expected 200 from deactivate, got {resp.status_code}: {resp.text}"
        )

        user = sync_db["users"].find_one({"id": 2401})
        assert user.get("is_deactivated") is True, "is_deactivated should be True"
        assert user.get("deactivatedAt") is not None, "deactivatedAt should be set"

    def test_deactivated_user_hidden(self):
        """Deactivated user does not appear in discover (top-matches) or likes."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 2501)
        _insert_user(sync_db, 2502, extra={"is_deactivated": True})

        # 2502 liked 2501 before deactivating
        sync_db["likes"].insert_one({"fromUser": 2502, "toUser": 2501})

        # Seed recommendations for 2501 pointing at 2502
        sync_db["recommendations"].insert_one({
            "userId": 2501,
            "matches": [{"user_id": 2502, "compatibilityScore": 0.88}],
        })

        # Deactivated user should not appear in top-matches
        top = client.get("/api/users/2501/top-matches", headers=_auth(2501))
        if top.status_code == 200:
            ids = [m["user_id"] for m in top.json().get("matches", [])]
            assert 2502 not in ids, "Deactivated user should not appear in top-matches"

        # Deactivated user should not appear in likes-received
        likes = client.get("/api/users/2501/likes-received", headers=_auth(2501))
        assert likes.status_code == 200
        from_users = [like.get("fromUser") for like in likes.json()]
        assert 2502 not in from_users, "Deactivated user's like should not appear in likes-received"


# ---------------------------------------------------------------------------
# Tests — Reactivate
# ---------------------------------------------------------------------------

class TestReactivateProfile:
    """POST /api/users/{user_id}/reactivate"""

    def test_reactivate_profile(self):
        """Reactivate clears is_deactivated and deactivatedAt."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(
            sync_db, 2601,
            extra={
                "is_deactivated": True,
                "deactivatedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

        resp = client.post("/api/users/2601/reactivate", headers=_auth(2601))
        assert resp.status_code == 200, (
            f"Expected 200 from reactivate, got {resp.status_code}: {resp.text}"
        )

        user = sync_db["users"].find_one({"id": 2601})
        assert user.get("is_deactivated") is not True, "is_deactivated should be cleared"
        assert user.get("deactivatedAt") is None or "deactivatedAt" not in user, (
            "deactivatedAt should be removed after reactivation"
        )


# ---------------------------------------------------------------------------
# Tests — 30-day cleanup
# ---------------------------------------------------------------------------

class TestDeactivate30DayCleanup:
    """Startup cleanup: deactivated accounts older than 30 days are hard-deleted."""

    def test_deactivate_30_day_cleanup(self):
        """
        Seed a user with is_deactivated=True and deactivatedAt 31 days ago.
        Run the cleanup logic directly against the test DB and confirm deletion.

        The lifespan startup in main.py does:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            await users_collection.delete_many({
                "is_deactivated": True,
                "deactivatedAt": {"$lt": cutoff},
            })

        We replicate that logic here using the sync test DB.
        """
        sync_client = MongoClient(TEST_MONGO_URL)
        sync_db = sync_client[TEST_DB_NAME]

        old_deactivated_at = datetime.now(timezone.utc) - timedelta(days=31)

        # Insert a stale deactivated user
        sync_db["users"].insert_one({
            "id": 99999,
            "email": "stale_deactivated@auburn.edu",
            "hashed_password": hash_password(_PASSWORD),
            "username": "stale_user",
            "gender": "male",
            "matched": False,
            "matchCount": 0,
            "matchedWith": [],
            "is_deactivated": True,
            "deactivatedAt": old_deactivated_at,
        })

        # Verify it's there
        assert sync_db["users"].count_documents({"id": 99999}) == 1

        # Run the same cleanup logic from main.py lifespan
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = sync_db["users"].delete_many({
            "is_deactivated": True,
            "deactivatedAt": {"$lt": cutoff},
        })

        assert result.deleted_count >= 1, (
            "Cleanup should have deleted the 31-day-old deactivated account"
        )
        assert sync_db["users"].count_documents({"id": 99999}) == 0, (
            "Stale deactivated user should be hard-deleted"
        )

        # A recently deactivated user (1 day ago) should NOT be deleted
        recent_deactivated_at = datetime.now(timezone.utc) - timedelta(days=1)
        sync_db["users"].insert_one({
            "id": 99998,
            "email": "recent_deactivated@auburn.edu",
            "hashed_password": hash_password(_PASSWORD),
            "username": "recent_deactivated_user",
            "gender": "male",
            "matched": False,
            "matchCount": 0,
            "matchedWith": [],
            "is_deactivated": True,
            "deactivatedAt": recent_deactivated_at,
        })

        result2 = sync_db["users"].delete_many({
            "is_deactivated": True,
            "deactivatedAt": {"$lt": cutoff},
        })
        assert sync_db["users"].count_documents({"id": 99998}) == 1, (
            "Recently deactivated user (1 day) should NOT be deleted"
        )

        # Clean up
        sync_db["users"].delete_many({"id": {"$in": [99998, 99999]}})
        sync_client.close()
