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
        from_gender = (from_user.get("gender") or "").lower()
        to_gender = (to_user.get("gender") or "").lower()
        if from_gender and to_gender and from_gender != to_gender:
            raise ValueError("Cannot like a user of a different gender.")

        from_matched_with = _normalize_matched_with(from_user)
        to_matched_with = _normalize_matched_with(to_user)

        if len(from_matched_with) >= MAX_MATCHES:
            raise ValueError(f"You already have {MAX_MATCHES} matches")
        if len(to_matched_with) >= MAX_MATCHES:
            raise ValueError(f"That user already has {MAX_MATCHES} matches")
        if to_id in from_matched_with:
            raise ValueError("Already matched with this user")

        # Check both like directions upfront
        already_liked = await self.likes.find_one({"fromUser": from_id, "toUser": to_id})
        mutual_like = await self.likes.find_one({"fromUser": to_id, "toUser": from_id})

        # If already liked and no mutual yet — nothing new to do
        if already_liked and not mutual_like:
            raise ValueError("Already liked this user")

        if not already_liked:
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

        # If mutual (normal or stale recovery), create the match
        if mutual_like:
            # Re-fetch for fresh data
            from_user = await self.users.find_one({"id": from_id})
            to_user = await self.users.find_one({"id": to_id})
            from_matched_with = _normalize_matched_with(from_user)
            to_matched_with = _normalize_matched_with(to_user)

            if len(from_matched_with) >= MAX_MATCHES or len(to_matched_with) >= MAX_MATCHES:
                if not already_liked:
                    await self.likes.delete_one({"fromUser": from_id, "toUser": to_id})
                raise ValueError("One of the users reached max matches during processing")

            new_from_matched = from_matched_with + [to_id]
            new_to_matched = to_matched_with + [from_id]
            new_from_count = len(new_from_matched)
            new_to_count = len(new_to_matched)

            await self.users.update_one(
                {"id": from_id},
                {"$set": {"matchedWith": new_from_matched, "matched": True, "matchCount": new_from_count}}
            )
            await self.users.update_one(
                {"id": to_id},
                {"$set": {"matchedWith": new_to_matched, "matched": True, "matchCount": new_to_count}}
            )

            await self.matches.insert_one({
                "user1_id": from_id,
                "user2_id": to_id,
                "confirmedAt": datetime.utcnow()
            })

            from_username = from_user.get("username", f"User #{from_id}")
            to_username = to_user.get("username", f"User #{to_id}")
            await self._create_notification(
                "match_created", to_id, from_id,
                f"You matched with {to_username}! Start chatting now."
            )
            await self._create_notification(
                "match_created", from_id, to_id,
                f"You matched with {from_username}! Start chatting now."
            )

            # Clean up like records — no longer needed after match
            await self.likes.delete_many({
                "$or": [
                    {"fromUser": from_id, "toUser": to_id},
                    {"fromUser": to_id, "toUser": from_id},
                ]
            })

            # Remove each other from recommendations
            await self.recommendations.update_one(
                {"userId": from_id},
                {"$pull": {"matches": {"user_id": to_id}}}
            )
            await self.recommendations.update_one(
                {"userId": to_id},
                {"$pull": {"matches": {"user_id": from_id}}}
            )

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
        """Return pending likes received by user (excludes already-matched users)."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            return []

        matched_with = _normalize_matched_with(user)

        # If user is at max matches, no point showing likes
        if len(matched_with) >= MAX_MATCHES:
            return []

        cursor = self.likes.find({"toUser": user_id})
        likes = []
        async for like in cursor:
            # Skip if already matched with this sender
            if like["fromUser"] in matched_with:
                continue
            like["_id"] = str(like["_id"])
            likes.append(like)
        return likes

    async def get_likes_sent(self, user_id: int) -> list[int]:
        """Return IDs of users that user_id has liked but not yet matched with."""
        user = await self.users.find_one({"id": user_id})
        matched_with = _normalize_matched_with(user) if user else []

        cursor = self.likes.find({"fromUser": user_id})
        sent = []
        async for like in cursor:
            to_id = like["toUser"]
            # Skip if already matched (mutual like became a match)
            if to_id in matched_with:
                continue
            sent.append(to_id)
        return sent

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

        # Use $set instead of $pull to safely handle legacy null/int matchedWith fields
        await self.users.update_one(
            {"id": user_id},
            {"$set": {"matchedWith": new_user_matches, "matchCount": new_user_count, "matched": new_user_count > 0}}
        )

        partner = await self.users.find_one({"id": partner_id})
        if partner:
            partner_matched_with = _normalize_matched_with(partner)
            new_partner_matches = [x for x in partner_matched_with if x != user_id]
            new_partner_count = len(new_partner_matches)

            await self.users.update_one(
                {"id": partner_id},
                {"$set": {"matchedWith": new_partner_matches, "matchCount": new_partner_count, "matched": new_partner_count > 0}}
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
