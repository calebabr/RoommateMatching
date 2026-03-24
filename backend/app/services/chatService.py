from datetime import datetime
from app.database import chat_collection, users_collection

class ChatService:
    def __init__(self):
        self.messages = chat_collection
        self.users = users_collection

    async def send_message(self, from_id: int, content: str) -> dict:
        """Send a message to matched partner."""
        from_user = await self.users.find_one({"id": from_id})
        if not from_user:
            raise ValueError("User not found")
        if not from_user.get("matched"):
            raise ValueError("You are not matched with anyone")

        to_id = from_user.get("matchedWith")
        if not to_id:
            raise ValueError("No matched partner found")

        msg = {
            "fromUser": from_id,
            "toUser": to_id,
            "content": content,
            "createdAt": datetime.utcnow()
        }
        result = await self.messages.insert_one(msg)
        msg["_id"] = str(result.inserted_id)
        msg["id"] = msg["_id"]
        return msg

    async def get_messages(self, user_id: int, limit: int = 100) -> list[dict]:
        """Get all messages between user and their matched partner."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        if not user.get("matched"):
            return []

        partner_id = user.get("matchedWith")
        if not partner_id:
            return []

        cursor = self.messages.find({
            "$or": [
                {"fromUser": user_id, "toUser": partner_id},
                {"fromUser": partner_id, "toUser": user_id},
            ]
        }).sort("createdAt", 1).limit(limit)

        messages = []
        async for msg in cursor:
            msg["id"] = str(msg["_id"])
            msg.pop("_id", None)
            messages.append(msg)
        return messages