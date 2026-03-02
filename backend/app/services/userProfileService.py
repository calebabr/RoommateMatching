from datetime import datetime
from app.database import users_collection, likes_collection, recommendations_collection, matches_collection

class UserProfileService:
    def __init__(self):
        self.collection = users_collection

    async def get_next_id(self) -> int:
        """
        Retrieves the next available user ID by finding the maximum existing ID and incrementing it.
        
        Parameters:
            None
        
        Returns:
            int: The next available user ID. Returns 1 if no users exist.
        """
        last_user = await self.collection.find_one(sort=[("id", -1)])
        if last_user:
            return last_user["id"] + 1
        return 1

    async def create_user(self, user_data: dict) -> dict:
        """
        Creates a new user account with provided information.
        
        Parameters:
            user_data (dict): Dictionary containing user information (username, password, preferences, etc.)
        
        Returns:
            dict: The created user object with assigned ID and metadata.
        
        Raises:
            ValueError: If username already exists in the database.
        """
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
        """
        Retrieves a user profile by user ID.
        
        Parameters:
            user_id (int): The unique identifier of the user to retrieve.
        
        Returns:
            dict: The user object containing all profile information.
        
        Raises:
            ValueError: If user with the specified ID does not exist.
        """
        user = await self.collection.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        user.pop("_id", None)
        return user

    async def update_profile(self, user_id: int, preferences: dict) -> dict:
        """
        Updates a user's profile with new preference information.
        
        Parameters:
            user_id (int): The unique identifier of the user to update.
            preferences (dict): Dictionary of preference fields to update.
        
        Returns:
            dict: The updated user profile object.
        
        Raises:
            ValueError: If user not found or if user is already matched.
        """
        user = await self.collection.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        if user.get("matched"):
            raise ValueError("Cannot update profile while matched")

        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": preferences},
            return_document=True
        )
        result.pop("_id", None)
        return result

    async def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user account and all associated data including matches, likes, and recommendations.
        
        Parameters:
            user_id (int): The unique identifier of the user to delete.
        
        Returns:
            bool: True if user was successfully deleted, False if user did not exist.
        
        Notes:
            Automatically unmatches the user's partner if they are currently matched.
            Removes all likes sent by and received by the user.
            Removes user from recommendations for all other users.
        """
        user = await self.collection.find_one({"id": user_id})
        if not user:
            return False

        # If matched, unmatch partner first
        if user.get("matched") and user.get("matchedWith"):
            partner_id = user["matchedWith"]
            await self.collection.update_one(
                {"id": partner_id},
                {"$set": {"matched": False, "matchedWith": None}}
            )
            await matches_collection.delete_many({
                "$or": [
                    {"user1_id": user_id, "user2_id": partner_id},
                    {"user1_id": partner_id, "user2_id": user_id},
                ]
            })

        # Delete user
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

        return result.deleted_count > 0

    async def get_all_active_users(self) -> list[dict]:
        """
        Retrieves all users who are currently not matched.
        
        Parameters:
            None
        
        Returns:
            list[dict]: List of all unmatched user objects.
        """
        cursor = self.collection.find({"matched": False})
        users = []
        async for user in cursor:
            user.pop("_id", None)
            users.append(user)
        return users

    async def mark_matched(self, user_id: int, matched_with: int) -> dict:
        """
        Marks a user as matched with another user.
        
        Parameters:
            user_id (int): The user ID to mark as matched.
            matched_with (int): The user ID of the matched partner.
        
        Returns:
            dict: The updated user profile object with matched status.
        
        Raises:
            ValueError: If user with the specified ID does not exist.
        """
        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"matched": True, "matchedWith": matched_with}},
            return_document=True
        )
        if not result:
            raise ValueError(f"User {user_id} not found")
        result.pop("_id", None)
        return result

    async def unmatch_user(self, user_id: int) -> dict:
        """
        Unmatches a user from their current match partner.
        
        Parameters:
            user_id (int): The user ID to unmatch.
        
        Returns:
            dict: The updated user profile object with matched status set to False.
        
        Raises:
            ValueError: If user with the specified ID does not exist.
        """
        result = await self.collection.find_one_and_update(
            {"id": user_id},
            {"$set": {"matched": False, "matchedWith": None}},
            return_document=True
        )
        if not result:
            raise ValueError(f"User {user_id} not found")
        result.pop("_id", None)
        return result