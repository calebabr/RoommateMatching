from datetime import datetime
from app.services.matchScore import matchScore
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
            # Gender filter: only same-gender candidates
            if not self.scorer.genderCompatible(target_user, user):
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
        result = await self.recommendations.find_one({"userId": user_id})
        if not result:
            return []
        return result.get("matches", [])

    async def on_new_user(self, new_user: dict, all_users: list[dict]):
        await self.recompute_for_user(new_user, all_users)
        for user in all_users:
            if user["id"] != new_user["id"]:
                await self.recompute_for_user(user, all_users)

    async def on_user_matched(self, matched_user_id: int):
        await self.recommendations.update_many(
            {},
            {"$pull": {"matches": {"user_id": matched_user_id}}}
        )
        await self.recommendations.delete_one({"userId": matched_user_id})

    async def on_user_unmatched(self, user_id: int, all_users: list[dict]):
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
        for user in all_users:
            await self.recompute_for_user(user, all_users)