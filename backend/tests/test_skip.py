"""
Tests for P3FT.4 — Skip / Swipe endpoint.

Expected endpoint: POST /api/users/{user_id}/skip/{target_id}

The swipes collection already exists in app/database.py and the top-matches
endpoint already reads from it to exclude skipped users. These tests define
the contract for the skip endpoint itself.

Scenarios:
  1. test_skip_user                          — skip returns 200 {"message": "Skipped"}
  2. test_skip_self                          — skipping yourself returns 400
  3. test_skip_unauthenticated               — no token returns 401/403
  4. test_skipped_user_excluded_from_discover — after skip, target absent from top-matches
  5. test_skip_upsert                         — skipping the same user twice → no duplicates
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
def patch_skip_collections():
    """Patch all collections used by the skip endpoint and top-matches filtering."""
    from tests.helpers import FullAsyncMongoWrapper
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.auth.dependencies as deps

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    users_col = FullAsyncMongoWrapper(sync_db["users"])
    swipes_col = FullAsyncMongoWrapper(sync_db["swipes"])
    recs_col = FullAsyncMongoWrapper(sync_db["recommendations"])
    blocks_col = FullAsyncMongoWrapper(sync_db["blocks"])

    orig_swipes = dbmod.swipes_collection
    orig_users_dbmod = dbmod.users_collection
    orig_blocks_dbmod = dbmod.blocks_collection
    orig_users_deps = deps.users_collection
    orig_blocks_deps = deps.blocks_collection
    orig_profile_col = rv.userProfileService.collection
    orig_rec_col = rv.recommendationService.collection
    orig_block_blocks = rv.blockService.blocks
    orig_block_users = rv.blockService.users

    dbmod.swipes_collection = swipes_col
    dbmod.users_collection = users_col
    dbmod.blocks_collection = blocks_col
    deps.users_collection = users_col
    deps.blocks_collection = blocks_col
    rv.userProfileService.collection = users_col
    rv.recommendationService.collection = recs_col
    rv.blockService.blocks = blocks_col
    rv.blockService.users = users_col

    # Patch module-level names used directly in route handlers (imported at top of userRoutes)
    import app.routers.userRoutes as ur_mod
    orig_swipes_ur = getattr(ur_mod, "swipes_collection", None)
    orig_users_ur = getattr(ur_mod, "users_collection", None)
    ur_mod.swipes_collection = swipes_col
    ur_mod.users_collection = users_col

    for col in ["users", "swipes", "recommendations", "blocks"]:
        sync_db[col].delete_many({})

    yield

    dbmod.swipes_collection = orig_swipes
    dbmod.users_collection = orig_users_dbmod
    dbmod.blocks_collection = orig_blocks_dbmod
    deps.users_collection = orig_users_deps
    deps.blocks_collection = orig_blocks_deps
    rv.userProfileService.collection = orig_profile_col
    rv.recommendationService.collection = orig_rec_col
    rv.blockService.blocks = orig_block_blocks
    rv.blockService.users = orig_block_users
    if orig_swipes_ur is not None:
        ur_mod.swipes_collection = orig_swipes_ur
    if orig_users_ur is not None:
        ur_mod.users_collection = orig_users_ur

    for col in ["users", "swipes", "recommendations", "blocks"]:
        sync_db[col].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(sync_db, user_id: int) -> dict:
    doc = {
        "id": user_id,
        "email": f"skip{user_id}@auburn.edu",
        "hashed_password": hash_password("Password1!"),
        "username": f"skipuser{user_id}",
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
    sync_db["users"].insert_one(doc)
    return doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSkipUser:
    """POST /api/users/{user_id}/skip/{target_id}"""

    def test_skip_user(self):
        """Skipping a user returns 200 with message 'Skipped'."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3001)
        _insert_user(sync_db, 3002)

        resp = client.post("/api/users/3001/skip/3002", headers=_auth(3001))
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data.get("message") == "Skipped", (
            f"Expected message='Skipped', got: {data}"
        )

    def test_skip_self(self):
        """Skipping your own user ID returns 400."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3101)

        resp = client.post("/api/users/3101/skip/3101", headers=_auth(3101))
        assert resp.status_code == 400, (
            f"Expected 400 for self-skip, got {resp.status_code}: {resp.text}"
        )

    def test_skip_unauthenticated(self):
        """No token → 401 or 403."""
        resp = client.post("/api/users/3201/skip/3202")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403, got {resp.status_code}"
        )

    def test_skipped_user_excluded_from_discover(self):
        """After skipping user B, user B no longer appears in A's top-matches.

        The top-matches handler already reads swipes_collection to build excluded_ids.
        This test verifies that skip writes to swipes_collection with the right shape,
        and the filtering works end-to-end.
        """
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3301)
        _insert_user(sync_db, 3302)

        # Seed a recommendation so top-matches has data
        sync_db["recommendations"].insert_one({
            "userId": 3301,
            "matches": [{"user_id": 3302, "compatibilityScore": 0.85}],
        })

        # A skips B
        skip_resp = client.post("/api/users/3301/skip/3302", headers=_auth(3301))
        assert skip_resp.status_code == 200, (
            f"Skip should succeed first, got {skip_resp.status_code}: {skip_resp.text}"
        )

        # B should not appear in A's top-matches
        top = client.get("/api/users/3301/top-matches", headers=_auth(3301))
        if top.status_code == 200:
            ids = [m["user_id"] for m in top.json().get("matches", [])]
            assert 3302 not in ids, (
                "Skipped user 3302 should not appear in 3301's top-matches"
            )
        elif top.status_code == 404:
            pass  # No matches left — skip filtered everything out, which is correct
        else:
            pytest.fail(f"Unexpected status {top.status_code}: {top.text}")

    def test_skip_upsert(self):
        """Skipping the same user twice does not create duplicate documents.

        The endpoint should upsert — a second skip returns 200 but the swipes
        collection should still contain only one document for the pair.
        """
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3401)
        _insert_user(sync_db, 3402)

        resp1 = client.post("/api/users/3401/skip/3402", headers=_auth(3401))
        assert resp1.status_code == 200

        resp2 = client.post("/api/users/3401/skip/3402", headers=_auth(3401))
        assert resp2.status_code == 200, (
            f"Second skip should not error, got {resp2.status_code}: {resp2.text}"
        )

        count = sync_db["swipes"].count_documents({"user_id": 3401, "skipped_user_id": 3402})
        assert count == 1, (
            f"Expected exactly 1 swipe document after two skips, got {count}"
        )
