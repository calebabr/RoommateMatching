from datetime import datetime
from app.database import likes_collection, matches_collection, users_collection, recommendations_collection

class LikeService:
    def __init__(self):
        self.likes = likes_collection
        self.matches = matches_collection
        self.users = users_collection
        self.recommendations = recommendations_collection

    async def send_like(self, from_id: int, to_id: int) -> dict:
        """
        Sends a like from one user to another. Creates a match if both users like each other.

        Parameters:
            from_id (int): User ID sending the like.
            to_id (int): User ID receiving the like.

        Returns:
            dict: Status response with 'status' key ('liked' or 'matched') and relevant user ID.

        Raises:
            ValueError: If user tries to like themselves, target doesn't exist, already liked,
                        or either user is already matched.

        Notes:
            When mutual likes are detected, both users are marked as matched and all other
            pending likes are cleaned up. Recommendations are also removed for matched users.
        """
        # Cannot like yourself
        if from_id == to_id:
            raise ValueError("Cannot like yourself")

        # Check sender exists
        from_user = await self.users.find_one({"id": from_id})
        if not from_user:
            raise ValueError("User not found")

        # Check target exists
        to_user = await self.users.find_one({"id": to_id})
        if not to_user:
            raise ValueError("Target user not found")

        # Check if sender is already matched
        if from_user.get("matched"):
            raise ValueError(f"You (user {from_id}) are already matched with user {from_user.get('matchedWith')}")

        # Check if target is already matched
        if to_user.get("matched"):
            raise ValueError(f"User {to_id} is already matched with user {to_user.get('matchedWith')}")

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
            # Re-check neither got matched while processing
            from_user = await self.users.find_one({"id": from_id})
            to_user = await self.users.find_one({"id": to_id})
            if from_user.get("matched") or to_user.get("matched"):
                # Clean up the like we just inserted
                await self.likes.delete_one({"fromUser": from_id, "toUser": to_id})
                raise ValueError("One of the users got matched during processing")

            # Mark both users as matched in the users collection
            await self.users.update_one(
                {"id": from_id},
                {"$set": {"matched": True, "matchedWith": to_id}}
            )
            await self.users.update_one(
                {"id": to_id},
                {"$set": {"matched": True, "matchedWith": from_id}}
            )

            # Create match document
            match = {
                "user1_id": from_id,
                "user2_id": to_id,
                "confirmedAt": datetime.utcnow()
            }
            await self.matches.insert_one(match)

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
        """
        Retrieves all pending likes received by a user that require response.

        Parameters:
            user_id (int): The user ID to get likes for.

        Returns:
            list[dict]: List of like objects from users who are unmatched and haven't received a response.

        Notes:
            Filters out likes from already-matched users and likes where mutual response already exists.
        """
        cursor = self.likes.find({"toUser": user_id})
        likes = []
        async for like in cursor:
            # Skip likes from users who are already matched
            from_user = await self.users.find_one({"id": like["fromUser"]})
            if not from_user:
                continue
            if from_user.get("matched"):
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
        """
        Retrieves all confirmed matches for a user.

        Parameters:
            user_id (int): The user ID to get matches for.

        Returns:
            list[dict]: List of match objects where the user is either user1_id or user2_id.
        """
        cursor = self.matches.find({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        })
        matches = []
        async for match in cursor:
            match["_id"] = str(match["_id"])
            matches.append(match)
        return matches

    async def unmatch(self, user_id: int) -> dict:
        """
        Unmatches a user from their current match partner.

        Parameters:
            user_id (int): The user ID to unmatch.

        Returns:
            dict: Status object with 'unmatched_user' and 'was_matched_with' keys.

        Raises:
            ValueError: If user not found or user is not currently matched.

        Notes:
            Removes match record and cleans up mutual likes between the unmatched users.
            Both users are unmarked as matched.
        """
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        if not user.get("matched"):
            raise ValueError("User is not matched")

        matched_with = user.get("matchedWith")

        # Unmark both users
        await self.users.update_one(
            {"id": user_id},
            {"$set": {"matched": False, "matchedWith": None}}
        )
        if matched_with:
            await self.users.update_one(
                {"id": matched_with},
                {"$set": {"matched": False, "matchedWith": None}}
            )

        # Remove the match document
        await self.matches.delete_many({
            "$or": [
                {"user1_id": user_id, "user2_id": matched_with},
                {"user1_id": matched_with, "user2_id": user_id},
            ]
        })

        # Clean up the mutual likes between them
        await self.likes.delete_many({
            "$or": [
                {"fromUser": user_id, "toUser": matched_with},
                {"fromUser": matched_with, "toUser": user_id},
            ]
        })

        return {"unmatched_user": user_id, "was_matched_with": matched_with}