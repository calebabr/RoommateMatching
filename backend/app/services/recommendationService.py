from datetime import datetime
from app.services.matchScore import matchScore
from app.database import recommendations_collection

class RecommendationService:
    def __init__(self):
        self.scorer = matchScore()
        self.recommendations = recommendations_collection

    async def recompute_for_user(self, target_user: dict, candidate_users: list[dict], n=10):
        """
        Generates personalized match recommendations for a specific user.

        Parameters:
            target_user (dict): The user to generate recommendations for.
            candidate_users (list[dict]): Pool of candidate users to score against.
            n (int): Number of top matches to return (default 10).

        Returns:
            None (stores results in recommendations collection)

        Notes:
            Calculates compatibility scores with all candidates, filters for positive scores,
            and stores top n matches sorted by compatibility score in descending order.
        """
        scores = []
        for user in candidate_users:
            if user["id"] == target_user["id"]:
                continue
            score = self.scorer.compatibilityScore(target_user, user)
            if score > 0:
                scores.append({
                    "user_id": user["id"],
                    "compatibilityScore": round(score, 6)
                })

        scores.sort(key=lambda x: x["compatibilityScore"], reverse=True)
        top_matches = scores[:n]

        await self.recommendations.update_one(
            {"userId": target_user["id"]},
            {"$set": {"matches": top_matches, "computedAt": datetime.utcnow()}},
            upsert=True
        )

    async def get_top_matches(self, user_id: int) -> list[dict]:
        """
        Retrieves the stored top match recommendations for a user.

        Parameters:
            user_id (int): The user ID to get recommendations for.

        Returns:
            list[dict]: List of recommended users with their compatibility scores, or empty list if none exist.
        """
        result = await self.recommendations.find_one({"userId": user_id})
        if not result:
            return []
        return result.get("matches", [])

    async def on_new_user(self, new_user: dict, all_users: list[dict]):
        """
        Updates recommendations when a new user joins the platform.

        Parameters:
            new_user (dict): The newly created user profile.
            all_users (list[dict]): All user profiles including the new user.

        Returns:
            None (updates recommendation records in database)

        Notes:
            Generates recommendations for the new user and recomputes for all existing users.
        """
        await self.recompute_for_user(new_user, all_users)

        for user in all_users:
            if user["id"] != new_user["id"]:
                await self.recompute_for_user(user, all_users)

    async def on_user_matched(self, matched_user_id: int):
        """
        Removes a user from recommendations when they get matched.

        Parameters:
            matched_user_id (int): The user ID who just got matched.

        Returns:
            None (updates recommendations in database)

        Notes:
            Removes the matched user from all other users' recommendation lists.
            Deletes the matched user's own recommendations.
        """
        await self.recommendations.update_many(
            {},
            {"$pull": {"matches": {"user_id": matched_user_id}}}
        )
        await self.recommendations.delete_one({"userId": matched_user_id})

    async def on_user_unmatched(self, user_id: int, all_users: list[dict]):
        """
        Regenerates recommendations when a matched user becomes unmatched.

        Parameters:
            user_id (int): The user ID who just unmatched.
            all_users (list[dict]): All current user profiles.

        Returns:
            None (updates recommendation records in database)

        Notes:
            Regenerates recommendations for the unmatched user and all other users.
        """
        user_dict = None
        for u in all_users:
            if u["id"] == user_id:
                user_dict = u
                break

        if user_dict:
            await self.recompute_for_user(user_dict, all_users)
            for user in all_users:
                if user["id"] != user_id:
                    await self.recompute_for_user(user, all_users)

    async def recompute_all(self, all_users: list[dict]):
        """
        Regenerates recommendations for all users in the system.

        Parameters:
            all_users (list[dict]): All user profiles to generate recommendations for.

        Returns:
            None (updates all recommendation records in database)

        Notes:
            Useful for periodic recalculation or after major system updates.
        """
        for user in all_users:
            await self.recompute_for_user(user, all_users)