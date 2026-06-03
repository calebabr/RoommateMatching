"""Deletion service — soft-delete with 7-day restore window and data export."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import cloudinary
import cloudinary.uploader

from app.auth.utils import verify_password
from app.database import (
    users_collection,
    likes_collection,
    matches_collection,
    chat_collection,
    notifications_collection,
    blocks_collection,
    reports_collection,
    recommendations_collection,
)


def _normalize_matched_with(user: dict) -> list:
    mw = user.get("matchedWith")
    if mw is None:
        return []
    if isinstance(mw, list):
        return [x for x in mw if x is not None]
    if isinstance(mw, int):
        return [mw]
    return []


class DeletionService:
    def __init__(self):
        self.users = users_collection
        self.likes = likes_collection
        self.matches = matches_collection
        self.chat = chat_collection
        self.notifications = notifications_collection
        self.blocks = blocks_collection
        self.reports = reports_collection
        self.recommendations = recommendations_collection

    async def soft_delete_user(self, user_id: int, password: str) -> str:
        """Verify password, mark user deleted, return plain restore token.

        The plain token is returned to the caller (MVP: no email delivery).
        Only the SHA-256 hash is stored.
        """
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")

        hashed_pw = user.get("hashed_password", "")
        if not hashed_pw or not verify_password(password, hashed_pw):
            raise ValueError("Incorrect password")

        plain_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        expiry = datetime.now(timezone.utc) + timedelta(days=7)

        await self.users.update_one(
            {"id": user_id},
            {"$set": {
                "deletedAt": datetime.now(timezone.utc),
                "restoreToken": token_hash,
                "restoreTokenExpiry": expiry,
            }}
        )
        return plain_token

    async def restore_account(self, token: str) -> dict:
        """Find user by SHA-256 token hash (within expiry) and clear deletion fields."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        user = await self.users.find_one({
            "restoreToken": token_hash,
            "restoreTokenExpiry": {"$gt": now},
        })
        if not user:
            raise ValueError("Invalid or expired restore token")

        await self.users.update_one(
            {"id": user["id"]},
            {"$unset": {"deletedAt": "", "restoreToken": "", "restoreTokenExpiry": ""}}
        )

        user = await self.users.find_one({"id": user["id"]})
        user.pop("_id", None)
        user.pop("hashed_password", None)
        return user

    async def export_user_data(self, user_id: int) -> dict:
        """Aggregate all user data into a single exportable dict (no hashed_password)."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        user.pop("_id", None)
        user.pop("hashed_password", None)

        likes_sent = []
        async for doc in self.likes.find({"fromUser": user_id}):
            doc.pop("_id", None)
            likes_sent.append(doc)

        likes_received = []
        async for doc in self.likes.find({"toUser": user_id}):
            doc.pop("_id", None)
            likes_received.append(doc)

        user_matches = []
        async for doc in self.matches.find({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        }):
            doc.pop("_id", None)
            user_matches.append(doc)

        messages = []
        async for doc in self.chat.find({
            "$or": [{"fromUser": user_id}, {"toUser": user_id}]
        }):
            doc["_id"] = str(doc.pop("_id"))
            messages.append(doc)

        notifs = []
        async for doc in self.notifications.find({"toUser": user_id}):
            doc["_id"] = str(doc.pop("_id"))
            notifs.append(doc)

        return {
            "user": user,
            "likes_sent": likes_sent,
            "likes_received": likes_received,
            "matches": user_matches,
            "chat_messages": messages,
            "notifications": notifs,
        }

    async def hard_delete_user(self, user_id: int) -> None:
        """Permanently delete user and cascade to all related collections."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            return  # already gone

        # Remove from matched partners' matchedWith arrays
        partner_ids = _normalize_matched_with(user)
        for partner_id in partner_ids:
            partner = await self.users.find_one({"id": partner_id})
            if partner:
                p_mw = _normalize_matched_with(partner)
                new_p_mw = [x for x in p_mw if x != user_id]
                await self.users.update_one(
                    {"id": partner_id},
                    {"$set": {
                        "matchedWith": new_p_mw,
                        "matchCount": len(new_p_mw),
                        "matched": len(new_p_mw) > 0,
                    }}
                )

        # Cascade deletes
        await self.matches.delete_many({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        })
        await self.likes.delete_many({
            "$or": [{"fromUser": user_id}, {"toUser": user_id}]
        })
        await self.chat.delete_many({
            "$or": [{"fromUser": user_id}, {"toUser": user_id}]
        })
        await self.notifications.delete_many({
            "$or": [{"fromUser": user_id}, {"toUser": user_id}]
        })
        await self.blocks.delete_many({
            "$or": [{"blockerId": user_id}, {"blockedId": user_id}]
        })
        await self.reports.delete_many({
            "$or": [{"reporterUserId": user_id}, {"reportedUserId": user_id}]
        })
        await self.recommendations.update_many(
            {}, {"$pull": {"matches": {"user_id": user_id}}}
        )
        await self.recommendations.delete_one({"userId": user_id})

        # Delete Cloudinary photo if present
        photo_url = user.get("photoUrl", "")
        if photo_url and "cloudinary.com" in photo_url:
            try:
                public_id = photo_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                cloudinary.uploader.destroy(public_id)
            except Exception:
                pass  # Non-fatal

        await self.users.delete_one({"id": user_id})

    async def cleanup_expired_deletions(self) -> int:
        """Hard-delete users whose deletedAt is older than 30 days.

        Designed to be called once at startup (MVP). Returns count deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        cursor = self.users.find({
            "deletedAt": {"$exists": True, "$lt": cutoff}
        })
        expired = await cursor.to_list(length=None)
        count = 0
        for user in expired:
            await self.hard_delete_user(user["id"])
            count += 1
        return count
