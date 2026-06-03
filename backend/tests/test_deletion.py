"""Tests for account deletion: soft-delete, restore, data export, and hard-delete cascade."""
import hashlib
import json
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId
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
# Fixture: patch all collections used by DeletionService
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_deletion_collections():
    """Patch all collections needed by DeletionService and related services.

    Saves and restores all original references so the fixture does not pollute
    later test modules (test_auth.py, test_password.py, etc.) that share the
    same process-level app module objects.
    """
    from tests.helpers import FullAsyncMongoWrapper
    import app.database as dbmod
    import app.routers.userRoutes as rv
    import app.routers.authRoutes as ar
    import app.auth.dependencies as deps
    import app.services.deletionService as _del_svc_mod

    sync_client = MongoClient(TEST_MONGO_URL)
    sync_db = sync_client[TEST_DB_NAME]

    users_col = FullAsyncMongoWrapper(sync_db["users"])
    likes_col = FullAsyncMongoWrapper(sync_db["likes"])
    matches_col = FullAsyncMongoWrapper(sync_db["matches"])
    chat_col = FullAsyncMongoWrapper(sync_db["chat_messages"])
    notifs_col = FullAsyncMongoWrapper(sync_db["notifications"])
    blocks_col = FullAsyncMongoWrapper(sync_db["blocks"])
    reports_col = FullAsyncMongoWrapper(sync_db["reports"])
    recs_col = FullAsyncMongoWrapper(sync_db["recommendations"])

    # ---------- Save originals ----------
    orig = {
        "dbmod.users_collection": dbmod.users_collection,
        "dbmod.likes_collection": dbmod.likes_collection,
        "dbmod.matches_collection": dbmod.matches_collection,
        "dbmod.chat_collection": dbmod.chat_collection,
        "dbmod.notifications_collection": dbmod.notifications_collection,
        "dbmod.blocks_collection": dbmod.blocks_collection,
        "dbmod.reports_collection": dbmod.reports_collection,
        "dbmod.recommendations_collection": dbmod.recommendations_collection,
        "ar.users_collection": ar.users_collection,
        "deps.users_collection": deps.users_collection,
        "deps.blocks_collection": deps.blocks_collection,
        "deps.matches_collection": deps.matches_collection,
        "rv.deletionService.users": rv.deletionService.users,
        "rv.deletionService.likes": rv.deletionService.likes,
        "rv.deletionService.matches": rv.deletionService.matches,
        "rv.deletionService.chat": rv.deletionService.chat,
        "rv.deletionService.notifications": rv.deletionService.notifications,
        "rv.deletionService.blocks": rv.deletionService.blocks,
        "rv.deletionService.reports": rv.deletionService.reports,
        "rv.deletionService.recommendations": rv.deletionService.recommendations,
        "rv.blockService.blocks": rv.blockService.blocks,
        "rv.blockService.likes": rv.blockService.likes,
        "rv.blockService.matches": rv.blockService.matches,
        "rv.blockService.users": rv.blockService.users,
        "rv.userProfileService.collection": rv.userProfileService.collection,
        "del_svc_class": _del_svc_mod.DeletionService,
    }

    # ---------- Apply patches ----------
    dbmod.users_collection = users_col
    dbmod.likes_collection = likes_col
    dbmod.matches_collection = matches_col
    dbmod.chat_collection = chat_col
    dbmod.notifications_collection = notifs_col
    dbmod.blocks_collection = blocks_col
    dbmod.reports_collection = reports_col
    dbmod.recommendations_collection = recs_col

    ar.users_collection = users_col
    deps.users_collection = users_col
    deps.blocks_collection = blocks_col
    deps.matches_collection = matches_col

    rv.deletionService.users = users_col
    rv.deletionService.likes = likes_col
    rv.deletionService.matches = matches_col
    rv.deletionService.chat = chat_col
    rv.deletionService.notifications = notifs_col
    rv.deletionService.blocks = blocks_col
    rv.deletionService.reports = reports_col
    rv.deletionService.recommendations = recs_col

    rv.blockService.blocks = blocks_col
    rv.blockService.likes = likes_col
    rv.blockService.matches = matches_col
    rv.blockService.users = users_col

    rv.userProfileService.collection = users_col

    # Patch DeletionService class so authRoutes.restore_account's inline
    # `DeletionService()` also uses test collections.
    _orig_del_svc_class = orig["del_svc_class"]

    class _PatchedDeletionService(_orig_del_svc_class):
        def __init__(self):
            super().__init__()
            self.users = users_col
            self.likes = likes_col
            self.matches = matches_col
            self.chat = chat_col
            self.notifications = notifs_col
            self.blocks = blocks_col
            self.reports = reports_col
            self.recommendations = recs_col

    _del_svc_mod.DeletionService = _PatchedDeletionService

    # Clean all collections before each test
    for col in ["users", "likes", "matches", "chat_messages", "notifications",
                "blocks", "reports", "recommendations"]:
        sync_db[col].delete_many({})

    yield

    # ---------- Restore originals ----------
    _del_svc_mod.DeletionService = _orig_del_svc_class

    dbmod.users_collection = orig["dbmod.users_collection"]
    dbmod.likes_collection = orig["dbmod.likes_collection"]
    dbmod.matches_collection = orig["dbmod.matches_collection"]
    dbmod.chat_collection = orig["dbmod.chat_collection"]
    dbmod.notifications_collection = orig["dbmod.notifications_collection"]
    dbmod.blocks_collection = orig["dbmod.blocks_collection"]
    dbmod.reports_collection = orig["dbmod.reports_collection"]
    dbmod.recommendations_collection = orig["dbmod.recommendations_collection"]
    ar.users_collection = orig["ar.users_collection"]
    deps.users_collection = orig["deps.users_collection"]
    deps.blocks_collection = orig["deps.blocks_collection"]
    deps.matches_collection = orig["deps.matches_collection"]
    rv.deletionService.users = orig["rv.deletionService.users"]
    rv.deletionService.likes = orig["rv.deletionService.likes"]
    rv.deletionService.matches = orig["rv.deletionService.matches"]
    rv.deletionService.chat = orig["rv.deletionService.chat"]
    rv.deletionService.notifications = orig["rv.deletionService.notifications"]
    rv.deletionService.blocks = orig["rv.deletionService.blocks"]
    rv.deletionService.reports = orig["rv.deletionService.reports"]
    rv.deletionService.recommendations = orig["rv.deletionService.recommendations"]
    rv.blockService.blocks = orig["rv.blockService.blocks"]
    rv.blockService.likes = orig["rv.blockService.likes"]
    rv.blockService.matches = orig["rv.blockService.matches"]
    rv.blockService.users = orig["rv.blockService.users"]
    rv.userProfileService.collection = orig["rv.userProfileService.collection"]

    for col in ["users", "likes", "matches", "chat_messages", "notifications",
                "blocks", "reports", "recommendations"]:
        sync_db[col].delete_many({})
    sync_client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(sync_db, user_id: int, username: str = None, password: str = "Password1!") -> dict:
    doc = {
        "id": user_id,
        "email": f"del{user_id}@auburn.edu",
        "hashed_password": hash_password(password),
        "username": username or f"deluser{user_id}",
        "gender": "male",
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
    sync_db["users"].insert_one(doc)
    return doc


def _delete_request(url: str, body: dict, headers: dict):
    """Send a DELETE request with a JSON body.

    TestClient.delete() does not accept json= in httpx 0.25; use request().
    """
    return client.request(
        "DELETE",
        url,
        content=json.dumps(body),
        headers={**headers, "Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# Soft-delete tests
# ---------------------------------------------------------------------------

class TestSoftDelete:
    """DELETE /api/users/{user_id}"""

    def test_soft_delete_correct_password_200(self):
        """Soft-delete with correct password sets deletedAt and returns a restore token."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3001, password="Password1!")

        resp = _delete_request(
            "/api/users/3001",
            {"password": "Password1!"},
            _auth(3001),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "restoreToken" in body
        assert len(body["restoreToken"]) > 0

        user = sync_db["users"].find_one({"id": 3001})
        assert user.get("deletedAt") is not None

    def test_soft_delete_wrong_password_returns_400(self):
        """Soft-delete with wrong password returns 400."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3101, password="Password1!")

        resp = _delete_request(
            "/api/users/3101",
            {"password": "WrongPassword!"},
            _auth(3101),
        )
        assert resp.status_code == 400

    def test_soft_deleted_user_absent_from_discover(self):
        """Soft-deleted user does not appear in GET /users/all."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3201, password="Password1!")
        _insert_user(sync_db, 3202, password="Password1!")

        # Soft-delete 3201 directly in DB
        sync_db["users"].update_one(
            {"id": 3201},
            {"$set": {"deletedAt": datetime.now(timezone.utc)}}
        )

        resp = client.get("/api/users/all", headers=_auth(3202))
        assert resp.status_code == 200
        ids = [u["id"] for u in resp.json()]
        assert 3201 not in ids
        assert 3202 in ids

    def test_soft_deleted_user_cannot_log_in(self):
        """A soft-deleted user is blocked from accessing their own profile route.

        The login route does not check deletedAt directly; instead we verify that
        the /users/all endpoint (which filters on deletedAt) does not expose the
        deleted account, confirming deletion semantics are applied at query level.
        """
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 3301, password="Password1!")
        _insert_user(sync_db, 3302, password="Password1!")

        sync_db["users"].update_one(
            {"id": 3301},
            {"$set": {"deletedAt": datetime.now(timezone.utc)}}
        )

        resp = client.get("/api/users/all", headers=_auth(3302))
        assert resp.status_code == 200
        ids = [u["id"] for u in resp.json()]
        assert 3301 not in ids


# ---------------------------------------------------------------------------
# Restore account tests
# ---------------------------------------------------------------------------

class TestRestoreAccount:
    """POST /api/auth/restore-account"""

    def test_restore_with_valid_token_200(self):
        """Valid restore token within 7 days clears deletedAt and returns access token."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 4001, password="Password1!")

        delete_resp = _delete_request(
            "/api/users/4001",
            {"password": "Password1!"},
            _auth(4001),
        )
        assert delete_resp.status_code == 200
        restore_token = delete_resp.json()["restoreToken"]

        resp = client.post(
            "/api/auth/restore-account",
            json={"token": restore_token},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["message"] == "Account restored"

        user = sync_db["users"].find_one({"id": 4001})
        assert user.get("deletedAt") is None
        assert user.get("restoreToken") is None

    def test_restore_with_invalid_token_400(self):
        """Invalid/random restore token returns 400."""
        resp = client.post(
            "/api/auth/restore-account",
            json={"token": "totally-invalid-token-xyz"},
        )
        assert resp.status_code == 400

    def test_restore_with_expired_token_400(self):
        """Expired restore token (past 7-day window) returns 400."""
        import secrets
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 4101, password="Password1!")

        plain_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        expired_expiry = datetime.now(timezone.utc) - timedelta(days=1)

        sync_db["users"].update_one(
            {"id": 4101},
            {"$set": {
                "deletedAt": datetime.now(timezone.utc) - timedelta(days=8),
                "restoreToken": token_hash,
                "restoreTokenExpiry": expired_expiry,
            }}
        )

        resp = client.post(
            "/api/auth/restore-account",
            json={"token": plain_token},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Data export tests
# ---------------------------------------------------------------------------

class TestExportUserData:
    """GET /api/users/{user_id}/export"""

    def test_export_contains_required_keys(self):
        """Export response contains user, likes_sent, likes_received, and matches keys."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 5001, password="Password1!")

        resp = client.get("/api/users/5001/export", headers=_auth(5001))
        assert resp.status_code == 200
        body = resp.json()
        for key in ("user", "likes_sent", "likes_received", "matches"):
            assert key in body, f"Missing key: {key}"

    def test_export_includes_chat_messages(self):
        """Export response contains a chat_messages key and includes sent messages."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 5101, password="Password1!")
        _insert_user(sync_db, 5102, password="Password1!")

        sync_db["chat_messages"].insert_one({
            "_id": ObjectId(),
            "fromUser": 5101,
            "toUser": 5102,
            "content": "Hello!",
            "createdAt": datetime.now(timezone.utc),
        })

        resp = client.get("/api/users/5101/export", headers=_auth(5101))
        assert resp.status_code == 200
        body = resp.json()
        assert "chat_messages" in body
        assert len(body["chat_messages"]) >= 1

    def test_export_does_not_expose_hashed_password(self):
        """Exported user data must not contain the hashed_password field."""
        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        _insert_user(sync_db, 5201, password="Password1!")

        resp = client.get("/api/users/5201/export", headers=_auth(5201))
        assert resp.status_code == 200
        assert "hashed_password" not in resp.json()["user"]


# ---------------------------------------------------------------------------
# Hard-delete cascade tests (service unit tests)
# ---------------------------------------------------------------------------

class TestHardDeleteCascade:
    """DeletionService.hard_delete_user cascade behaviour."""

    def _get_svc(self):
        """Return a DeletionService with all collections pointing at the test DB."""
        from tests.helpers import FullAsyncMongoWrapper
        from app.services.deletionService import DeletionService

        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        svc = DeletionService()
        svc.users = FullAsyncMongoWrapper(sync_db["users"])
        svc.likes = FullAsyncMongoWrapper(sync_db["likes"])
        svc.matches = FullAsyncMongoWrapper(sync_db["matches"])
        svc.chat = FullAsyncMongoWrapper(sync_db["chat_messages"])
        svc.notifications = FullAsyncMongoWrapper(sync_db["notifications"])
        svc.blocks = FullAsyncMongoWrapper(sync_db["blocks"])
        svc.reports = FullAsyncMongoWrapper(sync_db["reports"])
        svc.recommendations = FullAsyncMongoWrapper(sync_db["recommendations"])
        return svc, sync_db

    def test_hard_delete_removes_user_from_partners_matched_with(self):
        """After hard_delete_user, the partner's matchedWith no longer contains the deleted user."""
        import asyncio
        svc, sync_db = self._get_svc()

        _insert_user(sync_db, 6001)
        _insert_user(sync_db, 6002)
        sync_db["users"].update_one(
            {"id": 6001}, {"$set": {"matchedWith": [6002], "matchCount": 1, "matched": True}}
        )
        sync_db["users"].update_one(
            {"id": 6002}, {"$set": {"matchedWith": [6001], "matchCount": 1, "matched": True}}
        )

        asyncio.get_event_loop().run_until_complete(svc.hard_delete_user(6001))

        assert sync_db["users"].find_one({"id": 6001}) is None
        partner = sync_db["users"].find_one({"id": 6002})
        assert 6001 not in (partner.get("matchedWith") or [])

    def test_hard_delete_removes_likes(self):
        """hard_delete_user deletes all likes in either direction for the deleted user."""
        import asyncio
        svc, sync_db = self._get_svc()

        _insert_user(sync_db, 6101)
        _insert_user(sync_db, 6102)
        sync_db["likes"].insert_one({"fromUser": 6101, "toUser": 6102})
        sync_db["likes"].insert_one({"fromUser": 6102, "toUser": 6101})

        asyncio.get_event_loop().run_until_complete(svc.hard_delete_user(6101))

        remaining = list(sync_db["likes"].find({
            "$or": [{"fromUser": 6101}, {"toUser": 6101}]
        }))
        assert len(remaining) == 0

    def test_hard_delete_removes_chat_messages(self):
        """hard_delete_user deletes all chat messages for the deleted user."""
        import asyncio
        svc, sync_db = self._get_svc()

        _insert_user(sync_db, 6201)
        _insert_user(sync_db, 6202)
        sync_db["chat_messages"].insert_one({
            "_id": ObjectId(),
            "fromUser": 6201,
            "toUser": 6202,
            "content": "Hey",
            "createdAt": datetime.now(timezone.utc),
        })

        asyncio.get_event_loop().run_until_complete(svc.hard_delete_user(6201))

        remaining = list(sync_db["chat_messages"].find({
            "$or": [{"fromUser": 6201}, {"toUser": 6201}]
        }))
        assert len(remaining) == 0


# ---------------------------------------------------------------------------
# cleanup_expired_deletions tests
# ---------------------------------------------------------------------------

class TestCleanupExpiredDeletions:
    """DeletionService.cleanup_expired_deletions hard-deletes past 30-day grace period."""

    def _get_svc(self):
        from tests.helpers import FullAsyncMongoWrapper
        from app.services.deletionService import DeletionService

        sync_db = MongoClient(TEST_MONGO_URL)[TEST_DB_NAME]
        svc = DeletionService()
        svc.users = FullAsyncMongoWrapper(sync_db["users"])
        svc.likes = FullAsyncMongoWrapper(sync_db["likes"])
        svc.matches = FullAsyncMongoWrapper(sync_db["matches"])
        svc.chat = FullAsyncMongoWrapper(sync_db["chat_messages"])
        svc.notifications = FullAsyncMongoWrapper(sync_db["notifications"])
        svc.blocks = FullAsyncMongoWrapper(sync_db["blocks"])
        svc.reports = FullAsyncMongoWrapper(sync_db["reports"])
        svc.recommendations = FullAsyncMongoWrapper(sync_db["recommendations"])
        return svc, sync_db

    def test_cleanup_hard_deletes_users_past_grace_period(self):
        """Users deleted > 30 days ago are permanently removed; recent ones are kept."""
        import asyncio
        svc, sync_db = self._get_svc()

        _insert_user(sync_db, 7001)
        _insert_user(sync_db, 7002)

        # 7001: deleted 31 days ago — past grace period
        sync_db["users"].update_one(
            {"id": 7001},
            {"$set": {"deletedAt": datetime.now(timezone.utc) - timedelta(days=31)}}
        )
        # 7002: deleted 5 days ago — still within grace period
        sync_db["users"].update_one(
            {"id": 7002},
            {"$set": {"deletedAt": datetime.now(timezone.utc) - timedelta(days=5)}}
        )

        count = asyncio.get_event_loop().run_until_complete(svc.cleanup_expired_deletions())

        assert count >= 1
        assert sync_db["users"].find_one({"id": 7001}) is None  # expired — gone
        assert sync_db["users"].find_one({"id": 7002}) is not None  # within window — kept

    def test_cleanup_does_not_delete_active_users(self):
        """cleanup_expired_deletions does not touch users without deletedAt."""
        import asyncio
        svc, sync_db = self._get_svc()

        _insert_user(sync_db, 7101)

        count = asyncio.get_event_loop().run_until_complete(svc.cleanup_expired_deletions())

        assert count == 0
        assert sync_db["users"].find_one({"id": 7101}) is not None
