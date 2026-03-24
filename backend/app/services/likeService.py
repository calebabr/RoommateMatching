from datetime import datetime
from app.database import likes_collection, matches_collection, users_collection, recommendations_collection, notifications_collection

class LikeService:
    def __init__(self):
        self.likes = likes_collection
        self.matches = matches_collection
        self.users = users_collection
        self.recommendations = recommendations_collection
        self.notifications = notifications_collection

    async def _create_notification(self, notif_type: str, from_user: int, to_user: int, message: str):
        """Create a notification record."""
        await self.notifications.insert_one({
            "type": notif_type,
            "fromUser": from_user,
            "toUser": to_user,
            "message": message,
            "read": False,
            "createdAt": datetime.utcnow()
        })

    async def send_like(self, from_id: int, to_id: int) -> dict:
        if from_id == to_id:
            raise ValueError("Cannot like yourself")

        from_user = await self.users.find_one({"id": from_id})
        if not from_user:
            raise ValueError("User not found")

        to_user = await self.users.find_one({"id": to_id})
        if not to_user:
            raise ValueError("Target user not found")

        # Gender check: only same-gender likes allowed
        from_gender = from_user.get("gender", "").lower()
        to_gender = to_user.get("gender", "").lower()
        if from_gender and to_gender and from_gender != to_gender:
            raise ValueError("Cannot like a user of a different gender. Males match with males, females match with females.")

        if from_user.get("matched"):
            raise ValueError(f"You (user {from_id}) are already matched with user {from_user.get('matchedWith')}")

        if to_user.get("matched"):
            raise ValueError(f"User {to_id} is already matched with user {to_user.get('matchedWith')}")

        existing = await self.likes.find_one({"fromUser": from_id, "toUser": to_id})
        if existing:
            raise ValueError("Already liked this user")

        await self.likes.insert_one({
            "fromUser": from_id,
            "toUser": to_id,
            "createdAt": datetime.utcnow()
        })

        # Notify the liked user
        from_username = from_user.get("username", f"User #{from_id}")
        await self._create_notification(
            "like_received", from_id, to_id,
            f"{from_username} liked you!"
        )

        # Check if mutual
        mutual = await self.likes.find_one({"fromUser": to_id, "toUser": from_id})
        if mutual:
            from_user = await self.users.find_one({"id": from_id})
            to_user = await self.users.find_one({"id": to_id})
            if from_user.get("matched") or to_user.get("matched"):
                await self.likes.delete_one({"fromUser": from_id, "toUser": to_id})
                raise ValueError("One of the users got matched during processing")

            await self.users.update_one(
                {"id": from_id},
                {"$set": {"matched": True, "matchedWith": to_id}}
            )
            await self.users.update_one(
                {"id": to_id},
                {"$set": {"matched": True, "matchedWith": from_id}}
            )

            match = {
                "user1_id": from_id,
                "user2_id": to_id,
                "confirmedAt": datetime.utcnow()
            }
            await self.matches.insert_one(match)

            # Notify both users about the match
            to_username = to_user.get("username", f"User #{to_id}")
            await self._create_notification(
                "match_created", to_id, from_id,
                f"You matched with {to_username}! Start chatting now."
            )
            await self._create_notification(
                "match_created", from_id, to_id,
                f"You matched with {from_username}! Start chatting now."
            )

            # Remove both from recommendations
            await self.recommendations.update_many(
                {},
                {"$pull": {"matches": {"user_id": from_id}}}
            )
            await self.recommendations.update_many(
                {},
                {"$pull": {"matches": {"user_id": to_id}}}
            )
            await self.recommendations.delete_one({"userId": from_id})
            await self.recommendations.delete_one({"userId": to_id})

            # Clean up all pending likes involving these users
            await self.likes.delete_many({
                "$or": [
                    {"fromUser": from_id, "toUser": {"$ne": to_id}},
                    {"toUser": from_id, "fromUser": {"$ne": to_id}},
                    {"fromUser": to_id, "toUser": {"$ne": from_id}},
                    {"toUser": to_id, "fromUser": {"$ne": from_id}},
                ]
            })

            return {"status": "matched", "matchedWith": to_id}

        return {"status": "liked", "likedUser": to_id}

    async def get_likes_received(self, user_id: int) -> list[dict]:
        cursor = self.likes.find({"toUser": user_id})
        likes = []
        async for like in cursor:
            from_user = await self.users.find_one({"id": like["fromUser"]})
            if not from_user:
                continue
            if from_user.get("matched"):
                continue

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

    async def unmatch(self, user_id: int) -> dict:
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        if not user.get("matched"):
            raise ValueError("User is not matched")

        matched_with = user.get("matchedWith")

        await self.users.update_one(
            {"id": user_id},
            {"$set": {"matched": False, "matchedWith": None}}
        )
        if matched_with:
            await self.users.update_one(
                {"id": matched_with},
                {"$set": {"matched": False, "matchedWith": None}}
            )

            # Notify the other user
            username = user.get("username", f"User #{user_id}")
            await self._create_notification(
                "unmatch", user_id, matched_with,
                f"{username} has unmatched with you."
            )

        await self.matches.delete_many({
            "$or": [
                {"user1_id": user_id, "user2_id": matched_with},
                {"user1_id": matched_with, "user2_id": user_id},
            ]
        })

        await self.likes.delete_many({
            "$or": [
                {"fromUser": user_id, "toUser": matched_with},
                {"fromUser": matched_with, "toUser": user_id},
            ]
        })

        return {"unmatched_user": user_id, "was_matched_with": matched_with}