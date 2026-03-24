from datetime import datetime
from app.database import likes_collection, matches_collection, users_collection, recommendations_collection, notifications_collection
from app.models import MAX_MATCHES


def _normalize_matched_with(user: dict) -> list:
    """Normalize matchedWith field to always be a list (handles old int/None format)."""
    mw = user.get("matchedWith")
    if mw is None:
        return []
    if isinstance(mw, list):
        return [x for x in mw if x is not None]
    if isinstance(mw, int):
        return [mw]
    return []


class LikeService:
    def __init__(self):
        self.likes = likes_collection
        self.matches = matches_collection
        self.users = users_collection
        self.recommendations = recommendations_collection
        self.notifications = notifications_collection

    async def _create_notification(self, notif_type: str, from_user: int, to_user: int, message: str):
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

        # Gender check
        from_gender = from_user.get("gender", "").lower()
        to_gender = to_user.get("gender", "").lower()
        if from_gender and to_gender and from_gender != to_gender:
            raise ValueError("Cannot like a user of a different gender.")

        from_matched_with = _normalize_matched_with(from_user)
        to_matched_with = _normalize_matched_with(to_user)

        from_count = len(from_matched_with)
        to_count = len(to_matched_with)

        if from_count >= MAX_MATCHES:
            raise ValueError(f"You already have {MAX_MATCHES} matches")
        if to_count >= MAX_MATCHES:
            raise ValueError(f"That user already has {MAX_MATCHES} matches")

        if to_id in from_matched_with:
            raise ValueError("Already matched with this user")

        existing = await self.likes.find_one({"fromUser": from_id, "toUser": to_id})
        if existing:
            raise ValueError("Already liked this user")

        await self.likes.insert_one({
            "fromUser": from_id,
            "toUser": to_id,
            "createdAt": datetime.utcnow()
        })

        from_username = from_user.get("username", f"User #{from_id}")
        await self._create_notification(
            "like_received", from_id, to_id,
            f"{from_username} liked you!"
        )

        # Check for mutual like
        mutual = await self.likes.find_one({"fromUser": to_id, "toUser": from_id})
        if mutual:
            # Re-fetch to avoid race conditions
            from_user = await self.users.find_one({"id": from_id})
            to_user = await self.users.find_one({"id": to_id})
            from_matched_with = _normalize_matched_with(from_user)
            to_matched_with = _normalize_matched_with(to_user)

            if len(from_matched_with) >= MAX_MATCHES or len(to_matched_with) >= MAX_MATCHES:
                await self.likes.delete_one({"fromUser": from_id, "toUser": to_id})
                raise ValueError("One of the users reached max matches during processing")

            new_from_count = len(from_matched_with) + 1
            new_to_count = len(to_matched_with) + 1

            await self.users.update_one(
                {"id": from_id},
                {"$push": {"matchedWith": to_id},
                 "$set": {"matched": True, "matchCount": new_from_count}}
            )
            await self.users.update_one(
                {"id": to_id},
                {"$push": {"matchedWith": from_id},
                 "$set": {"matched": True, "matchCount": new_to_count}}
            )

            await self.matches.insert_one({
                "user1_id": from_id,
                "user2_id": to_id,
                "confirmedAt": datetime.utcnow()
            })

            to_username = to_user.get("username", f"User #{to_id}")
            await self._create_notification(
                "match_created", to_id, from_id,
                f"You matched with {to_username}! Start chatting now."
            )
            await self._create_notification(
                "match_created", from_id, to_id,
                f"You matched with {from_username}! Start chatting now."
            )

            # Remove each other from recommendations
            await self.recommendations.update_one(
                {"userId": from_id},
                {"$pull": {"matches": {"user_id": to_id}}}
            )
            await self.recommendations.update_one(
                {"userId": to_id},
                {"$pull": {"matches": {"user_id": from_id}}}
            )

            # If either user is now full, remove them from all other recommendations
            if new_from_count >= MAX_MATCHES:
                await self.recommendations.update_many(
                    {}, {"$pull": {"matches": {"user_id": from_id}}}
                )
                await self.recommendations.delete_one({"userId": from_id})

            if new_to_count >= MAX_MATCHES:
                await self.recommendations.update_many(
                    {}, {"$pull": {"matches": {"user_id": to_id}}}
                )
                await self.recommendations.delete_one({"userId": to_id})

            return {"status": "matched", "matchedWith": to_id}

        return {"status": "liked", "likedUser": to_id}

    async def get_likes_received(self, user_id: int) -> list[dict]:
        """Return pending likes for user, only if user has room for more matches."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            return []

        matched_with = _normalize_matched_with(user)
        match_count = len(matched_with)

        # If user is at max matches, don't show any likes
        if match_count >= MAX_MATCHES:
            return []

        cursor = self.likes.find({"toUser": user_id})
        likes = []
        async for like in cursor:
            sender = await self.users.find_one({"id": like["fromUser"]})
            if not sender:
                continue

            sender_matched_with = _normalize_matched_with(sender)
            # Skip if sender is already at max matches
            if len(sender_matched_with) >= MAX_MATCHES:
                continue
            # Skip if already matched with this person
            if like["fromUser"] in matched_with:
                continue
            # Skip if user already liked back
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

    async def unmatch(self, user_id: int, partner_id: int) -> dict:
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")

        matched_with = _normalize_matched_with(user)
        if partner_id not in matched_with:
            raise ValueError("Not matched with this user")

        new_user_matches = [x for x in matched_with if x != partner_id]
        new_user_count = len(new_user_matches)

        await self.users.update_one(
            {"id": user_id},
            {"$pull": {"matchedWith": partner_id},
             "$set": {"matchCount": new_user_count, "matched": new_user_count > 0}}
        )

        partner = await self.users.find_one({"id": partner_id})
        if partner:
            partner_matched_with = _normalize_matched_with(partner)
            new_partner_matches = [x for x in partner_matched_with if x != user_id]
            new_partner_count = len(new_partner_matches)

            await self.users.update_one(
                {"id": partner_id},
                {"$pull": {"matchedWith": user_id},
                 "$set": {"matchCount": new_partner_count, "matched": new_partner_count > 0}}
            )

            username = user.get("username", f"User #{user_id}")
            await self._create_notification(
                "unmatch", user_id, partner_id,
                f"{username} has unmatched with you."
            )

        await self.matches.delete_many({
            "$or": [
                {"user1_id": user_id, "user2_id": partner_id},
                {"user1_id": partner_id, "user2_id": user_id},
            ]
        })

        await self.likes.delete_many({
            "$or": [
                {"fromUser": user_id, "toUser": partner_id},
                {"fromUser": partner_id, "toUser": user_id},
            ]
        })

        return {"unmatched_user": user_id, "was_matched_with": partner_id}
