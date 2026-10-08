"""P3FT.12 — "Found a roommate" status.

Distinct from the P3FT.3 profile pause: a paused user is taking a break, a
roommate-found user is done searching.  Both are hidden from discover,
likes-received and top-matches, but roommate-found additionally records an
`outcomes` document for future scoring-weight tuning.
"""
from datetime import datetime, timezone

from app.database import (
    users_collection,
    likes_collection,
    matches_collection,
    recommendations_collection,
    outcomes_collection,
)
from app.models import UserInDB
from app.services.matchScore import matchScore


class RoommateService:
    def __init__(self):
        self.users = users_collection
        self.likes = likes_collection
        self.matches = matches_collection
        self.recommendations = recommendations_collection
        self.outcomes = outcomes_collection
        self.scorer = matchScore()

    async def _is_current_match(self, user_id: int, partner_id: int) -> bool:
        doc = await self.matches.find_one({
            "$or": [
                {"user1_id": user_id, "user2_id": partner_id},
                {"user1_id": partner_id, "user2_id": user_id},
            ]
        })
        return doc is not None

    def _score(self, user_doc: dict, partner_doc: dict):
        """Compatibility score for the pair, or None if either profile is unscorable."""
        try:
            a = UserInDB(**user_doc).toMatchDict()
            b = UserInDB(**partner_doc).toMatchDict()
        except Exception:
            return None
        return round(self.scorer.compatibilityScore(a, b), 6)

    async def mark_found(self, user_id: int, partner_ids: list, via_app: bool) -> dict:
        """Mark the user as having found a roommate.

        - Sets roommateFound / roommateFoundAt / roommateFoundWith.
        - Cancels every pending like the user has sent.
        - Removes the user's recommendations document and pulls them out of
          everyone else's recommendation lists.
        - Writes an `outcomes` doc for each partner that is a real current match.

        Existing matches and chats are deliberately left untouched.
        """
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")

        now = datetime.now(timezone.utc)
        await self.users.update_one(
            {"id": user_id},
            {"$set": {
                "roommateFound": True,
                "roommateFoundAt": now,
                "roommateFoundWith": partner_ids,
            }},
        )

        # Pending (pre-match) likes this user sent are cancelled — a match record
        # is only ever created once the like is mutual, so every remaining like
        # from this user is still pending.
        await self.likes.delete_many({"fromUser": user_id})

        # Drop out of the recommendation pool in both directions.
        await self.recommendations.update_many(
            {}, {"$pull": {"matches": {"user_id": user_id}}}
        )
        await self.recommendations.delete_one({"userId": user_id})

        outcomes_recorded = 0
        for partner_id in partner_ids:
            if partner_id == user_id:
                continue
            if not await self._is_current_match(user_id, partner_id):
                continue  # only real in-app matches produce an outcome record
            partner = await self.users.find_one({"id": partner_id})
            if not partner:
                continue
            await self.outcomes.insert_one({
                "userId": user_id,
                "partnerId": partner_id,
                "compatibilityScore": self._score(user, partner),
                "viaApp": via_app,
                "recordedAt": now,
            })
            outcomes_recorded += 1

        return {
            "roommateFound": True,
            "roommateFoundAt": now,
            "roommateFoundWith": partner_ids,
            "outcomesRecorded": outcomes_recorded,
        }

    async def undo(self, user_id: int) -> dict:
        """Clear the roommate-found status and make the user visible again."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")

        await self.users.update_one(
            {"id": user_id},
            {
                "$set": {"roommateFound": False},
                "$unset": {"roommateFoundAt": "", "roommateFoundWith": ""},
            },
        )
        return {"roommateFound": False}
