from datetime import datetime
from app.database import likes_collection, matches_collection, users_collection

class LikeService:
    def __init__(self):
        self.likes = likes_collection
        self.matches = matches_collection
        self.users = users_collection

    async def send_like(self, from_id: int, to_id: int) -> dict:
        # Cannot like yourself
        if from_id == to_id:
            raise ValueError("Cannot like yourself")

        # Check if sender is already matched
        from_user = await self.users.find_one({"id": from_id})
        if not from_user:
            raise ValueError("User not found")
        if from_user.get("matched"):
            raise ValueError("You are already matched")

        # Check if target exists and is not matched
        to_user = await self.users.find_one({"id": to_id})
        if not to_user:
            raise ValueError("Target user not found")
        if to_user.get("matched"):
            raise ValueError("This user is already matched")

        # Check if already liked
        existing = await self.likes.find_one({"fromUser": from_id, "toUser": to_id})
        if existing:
            raise ValueError("Already liked this user")

        # Store the like
        await self.likes.insert_one({
            "fromUser": from_id,
            "toUser": to_id,
            "createdAt": datetime.utcnow()
        })

        # Check if mutual
        mutual = await self.likes.find_one({"fromUser": to_id, "toUser": from_id})
        if mutual:
            # Verify neither got matched while we were processing
            from_user_check = await self.users.find_one({"id": from_id})
            to_user_check = await self.users.find_one({"id": to_id})
            if from_user_check.get("matched") or to_user_check.get("matched"):
                raise ValueError("One of the users got matched during processing")

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
            # Skip likes from users who are already matched
            from_user = await self.users.find_one({"id": like["fromUser"]})
            if from_user and from_user.get("matched"):
                continue

            # Skip if I already responded
            already_responded = await self.likes.find_one({
                "fromUser": user_id,
                "toUser": like["fromUser"]
            })
            if already_responded:
                continue

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