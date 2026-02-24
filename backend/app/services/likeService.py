from datetime import datetime
from app.database import likes_collection, matches_collection

class LikeService:
    def __init__(self):
        self.likes = likes_collection
        self.matches = matches_collection

    async def send_like(self, from_id: int, to_id: int) -> dict:
        existing = await self.likes.find_one({"fromUser": from_id, "toUser": to_id})
        if existing:
            raise ValueError("Already liked this user")

        await self.likes.insert_one({
            "fromUser": from_id,
            "toUser": to_id,
            "createdAt": datetime.utcnow()
        })

        mutual = await self.likes.find_one({"fromUser": to_id, "toUser": from_id})
        if mutual:
            match = {
                "user1_id": from_id,
                "user2_id": to_id,
                "confirmedAt": datetime.utcnow()
            }
            await self.matches.insert_one(match)
            return {"status": "matched", "matchedWith": to_id}

        return {"status": "liked", "likedUser": to_id}

    async def get_likes_received(self, user_id: int) -> list[dict]:
        cursor = self.likes.find({"toUser": user_id})
        likes = []
        async for like in cursor:
            already_responded = await self.likes.find_one({
                "fromUser": user_id,
                "toUser": like["fromUser"]
            })
            if not already_responded:
                like["_id"] = str(like["_id"])
                likes.append(like)
        return likes

    async def get_matches(self, user_id: int) -> list[dict]:
        cursor = self.matches.find({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        })
        matches = []
        async for match in cursor:
            match["_id"] = str(match["_id"])
            matches.append(match)
        return matches