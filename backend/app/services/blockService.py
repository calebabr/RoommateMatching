"""Block service — handles user blocking, unblocking, and block-aware queries."""
from datetime import datetime, timezone
from app.database import blocks_collection, matches_collection, likes_collection, users_collection


def _normalize_matched_with(user: dict) -> list:
    mw = user.get("matchedWith")
    if mw is None:
        return []
    if isinstance(mw, list):
        return [x for x in mw if x is not None]
    if isinstance(mw, int):
        return [mw]
    return []


class BlockService:
    def __init__(self):
        self.blocks = blocks_collection
        self.matches = matches_collection
        self.likes = likes_collection
        self.users = users_collection

    async def block_user(self, blocker_id: int, blocked_id: int) -> None:
        """Insert block record, auto-unmatch the pair, delete pending likes."""
        if blocker_id == blocked_id:
            raise ValueError("Cannot block yourself")

        # Idempotent — don't error if block already exists
        existing = await self.blocks.find_one({"blockerId": blocker_id, "blockedId": blocked_id})
        if not existing:
            await self.blocks.insert_one({
                "blockerId": blocker_id,
                "blockedId": blocked_id,
                "createdAt": datetime.now(timezone.utc),
            })

        # Auto-unmatch the pair from the matches collection
        await self.matches.delete_many({
            "$or": [
                {"user1_id": blocker_id, "user2_id": blocked_id},
                {"user1_id": blocked_id, "user2_id": blocker_id},
            ]
        })

        # Update both users' matchedWith arrays and matchCount
        for uid, partner_id in [(blocker_id, blocked_id), (blocked_id, blocker_id)]:
            user = await self.users.find_one({"id": uid})
            if user:
                mw = _normalize_matched_with(user)
                if partner_id in mw:
                    new_mw = [x for x in mw if x != partner_id]
                    await self.users.update_one(
                        {"id": uid},
                        {"$set": {
                            "matchedWith": new_mw,
                            "matchCount": len(new_mw),
                            "matched": len(new_mw) > 0,
                        }}
                    )

        # Delete any pending likes between them in either direction
        await self.likes.delete_many({
            "$or": [
                {"fromUser": blocker_id, "toUser": blocked_id},
                {"fromUser": blocked_id, "toUser": blocker_id},
            ]
        })

    async def unblock_user(self, blocker_id: int, blocked_id: int) -> None:
        """Remove a block record. Does NOT restore a previously removed match."""
        await self.blocks.delete_one({"blockerId": blocker_id, "blockedId": blocked_id})

    async def is_blocked(self, user_a_id: int, user_b_id: int) -> bool:
        """Return True if either direction of a block exists between user_a and user_b."""
        doc = await self.blocks.find_one({
            "$or": [
                {"blockerId": user_a_id, "blockedId": user_b_id},
                {"blockerId": user_b_id, "blockedId": user_a_id},
            ]
        })
        return doc is not None

    async def get_blocked_ids(self, user_id: int) -> set:
        """Return a set of all user IDs blocked by OR blocking this user."""
        ids = set()
        async for doc in self.blocks.find({
            "$or": [{"blockerId": user_id}, {"blockedId": user_id}]
        }):
            if doc["blockerId"] == user_id:
                ids.add(doc["blockedId"])
            else:
                ids.add(doc["blockerId"])
        return ids

    async def get_blocked_by_user(self, user_id: int) -> list[dict]:
        """Return list of user documents that user_id has explicitly blocked."""
        blocked_ids = []
        async for doc in self.blocks.find({"blockerId": user_id}):
            blocked_ids.append(doc["blockedId"])

        users = []
        for uid in blocked_ids:
            user = await self.users.find_one({"id": uid})
            if user:
                user.pop("_id", None)
                user.pop("hashed_password", None)
                users.append(user)
        return users
