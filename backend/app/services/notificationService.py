from datetime import datetime
from app.database import notifications_collection

class NotificationService:
    def __init__(self):
        self.notifications = notifications_collection

    async def get_notifications(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get all notifications for a user, newest first."""
        cursor = self.notifications.find(
            {"toUser": user_id}
        ).sort("createdAt", -1).limit(limit)

        results = []
        async for notif in cursor:
            notif["id"] = str(notif["_id"])
            notif.pop("_id", None)
            results.append(notif)
        return results

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        return await self.notifications.count_documents({
            "toUser": user_id,
            "read": False
        })

    async def mark_all_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        result = await self.notifications.update_many(
            {"toUser": user_id, "read": False},
            {"$set": {"read": True}}
        )
        return result.modified_count

    async def mark_read(self, notification_id: str, user_id: int) -> bool:
        """Mark a single notification as read."""
        from bson import ObjectId
        result = await self.notifications.update_one(
            {"_id": ObjectId(notification_id), "toUser": user_id},
            {"$set": {"read": True}}
        )
        return result.modified_count > 0