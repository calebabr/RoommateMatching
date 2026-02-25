from datetime import datetime
from app.services.matchScore import matchScore
from app.services.clusterService import ClusterService
from app.database import recommendations_collection

class RecommendationService:
    def __init__(self):
        self.scorer = matchScore()
        self.recommendations = recommendations_collection

    async def recompute_for_user(self, target_user: dict, candidate_users: list[dict], n=10):
        scores = []
        for user in candidate_users:
            if user["id"] == target_user["id"]:
                continue
            score = self.scorer.compatibilityScore(target_user, user)
            if score > 0:
                scores.append({
                    "user_id": user["id"],
                    "compatibilityScore": score
                })

        scores.sort(key=lambda x: x["compatibilityScore"], reverse=True)
        top_matches = scores[:n]

        await self.recommendations.update_one(
            {"userId": target_user["id"]},
            {"$set": {"matches": top_matches, "computedAt": datetime.utcnow()}},
            upsert=True
        )

    async def get_top_matches(self, user_id: int) -> list[dict]:
        result = await self.recommendations.find_one({"userId": user_id})
        return result["matches"] if result else []

    async def on_new_user(self, new_user: dict, all_cluster_users: list[dict]):
        await self.recompute_for_user(new_user, all_cluster_users)

        for user in all_cluster_users:
            if user["id"] != new_user["id"]:
                await self.recompute_for_user(user, all_cluster_users)

    async def on_user_matched(self, matched_user_id: int):
        await self.recommendations.update_many(
            {},
            {"$pull": {"matches": {"user_id": matched_user_id}}}
        )
        await self.recommendations.delete_one({"userId": matched_user_id})

    async def recompute_all(self, all_users: list[dict]):
        for user in all_users:
            await self.recompute_for_user(user, all_users)