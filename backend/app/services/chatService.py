from datetime import datetime
from app.database import chat_collection, users_collection


def _normalize_matched_with(user: dict) -> list:
    mw = user.get("matchedWith")
    if mw is None:
        return []
    if isinstance(mw, list):
        return [x for x in mw if x is not None]
    if isinstance(mw, int):
        return [mw]
    return []


class ChatService:
    def __init__(self):
        self.messages = chat_collection
        self.users = users_collection

    async def send_message(self, from_id: int, partner_id: int, content: str) -> dict:
        """Send a message to a specific matched partner."""
        from_user = await self.users.find_one({"id": from_id})
        if not from_user:
            raise ValueError("User not found")

        matched_with = _normalize_matched_with(from_user)
        if partner_id not in matched_with:
            raise ValueError("You are not matched with this user")

        msg = {
            "fromUser": from_id,
            "toUser": partner_id,
            "content": content,
            "createdAt": datetime.utcnow()
        }
        result = await self.messages.insert_one(msg)
        msg["_id"] = str(result.inserted_id)
        msg["id"] = msg["_id"]
        return msg

    async def get_messages(self, user_id: int, partner_id: int, limit: int = 100) -> list[dict]:
        """Get all messages between user and a specific partner."""
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

    async def get_conversations(self, user_id: int) -> list[dict]:
        """Get the latest message for each matched partner (for chat list)."""
        user = await self.users.find_one({"id": user_id})
        if not user:
            return []

        matched_with = _normalize_matched_with(user)
        conversations = []

        for partner_id in matched_with:
            last_msg = await self.messages.find_one(
                {"$or": [
                    {"fromUser": user_id, "toUser": partner_id},
                    {"fromUser": partner_id, "toUser": user_id},
                ]},
                sort=[("createdAt", -1)]
            )
            conversations.append({
                "partnerId": partner_id,
                "lastMessage": {
                    "id": str(last_msg["_id"]) if last_msg else None,
                    "content": last_msg["content"] if last_msg else None,
                    "fromUser": last_msg["fromUser"] if last_msg else None,
                    "createdAt": last_msg["createdAt"] if last_msg else None,
                } if last_msg else None
            })

        return conversations
