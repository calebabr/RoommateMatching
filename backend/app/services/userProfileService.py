from datetime import datetime
from app.database import users_collection, likes_collection, recommendations_collection, matches_collection

class UserProfileService:
    def __init__(self):
        self.collection = users_collection

    async def get_next_id(self) -> int:
        last_user = await self.collection.find_one(sort=[("id", -1)])
        if last_user:
            return last_user["id"] + 1
        return 1

    async def create_user(self, user_data: dict) -> dict:
        existing = await self.collection.find_one({"username": user_data["username"]})
        if existing:
            raise ValueError("Username already exists")

        user_data["id"] = await self.get_next_id()
        user_data["matched"] = False
        user_data["matchedWith"] = None
        user_data["createdAt"] = datetime.utcnow()

        await self.collection.insert_one(user_data)
        user_data.pop("_id", None)
        return user_data

    async def get_user(self, user_id: int) -> dict:
        user = await self.collection.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        user.pop("_id", None)
        return user

    async def update_profile(self, user_id: int, preferences: dict) -> dict:
        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": preferences},
            return_document=True
        )
        if not result:
            raise ValueError("User not found")
        result.pop("_id", None)
        return result

    async def delete_user(self, user_id: int) -> bool:
        result = await self.collection.delete_one({"id": user_id})

        # Clean up all related data
        await likes_collection.delete_many({
            "$or": [{"fromUser": user_id}, {"toUser": user_id}]
        })
        await recommendations_collection.update_many(
            {},
            {"$pull": {"matches": {"user_id": user_id}}}
        )
        await recommendations_collection.delete_one({"userId": user_id})
        await matches_collection.delete_many({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        })

        # If they were matched, unmatch their partner
        partner = await self.collection.find_one({"matchedWith": user_id})
        if partner:
            await self.collection.update_one(
                {"id": partner["id"]},
                {"$set": {"matched": False, "matchedWith": None}}
            )

        return result.deleted_count > 0

    async def get_all_active_users(self) -> list[dict]:
        cursor = self.collection.find({"matched": False})
        users = []
        async for user in cursor:
            user.pop("_id", None)
            users.append(user)
        return users

    async def mark_matched(self, user_id: int, matched_with: int) -> dict:
        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"matched": True, "matchedWith": matched_with}},
            return_document=True
        )
        result.pop("_id", None)
        return result

    async def unmatch_user(self, user_id: int) -> dict:
        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"matched": False, "matchedWith": None}},
            return_document=True
        )
        result.pop("_id", None)
        return result