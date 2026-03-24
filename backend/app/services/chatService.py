from datetime import datetime
from app.database import messages_collection, matches_collection, users_collection


class ChatService:
    def __init__(self):
        self.messages = messages_collection
        self.matches = matches_collection
        self.users = users_collection

    def _conversation_id(self, user1_id: int, user2_id: int) -> str:
        """Deterministic conversation ID: smaller ID first."""
        a, b = sorted([user1_id, user2_id])
        return f"{a}_{b}"

    async def _get_match(self, user1_id: int, user2_id: int):
        """Find the match document between two users."""
        return await self.matches.find_one({
            "$or": [
                {"user1_id": user1_id, "user2_id": user2_id},
                {"user1_id": user2_id, "user2_id": user1_id},
            ]
        })

    async def _verify_can_chat(self, user1_id: int, user2_id: int):
        """Verify both users exist and have an active match."""
        u1 = await self.users.find_one({"id": user1_id})
        u2 = await self.users.find_one({"id": user2_id})
        if not u1 or not u2:
            raise ValueError("User not found")

        match = await self._get_match(user1_id, user2_id)
        if not match:
            raise ValueError("You can only chat with matched users")

    async def send_message(self, sender_id: int, receiver_id: int, text: str) -> dict:
        """Send a message from sender to receiver."""
        if sender_id == receiver_id:
            raise ValueError("Cannot message yourself")

        text = text.strip()
        if not text:
            raise ValueError("Message cannot be empty")
        if len(text) > 2000:
            raise ValueError("Message too long (max 2000 characters)")

        await self._verify_can_chat(sender_id, receiver_id)

        conv_id = self._conversation_id(sender_id, receiver_id)
        now = datetime.utcnow()
        msg = {
            "conversationId": conv_id,
            "senderId": sender_id,
            "receiverId": receiver_id,
            "text": text,
            "sentAt": now,
        }
        result = await self.messages.insert_one(msg)
        msg["_id"] = str(result.inserted_id)

        # Denormalize: update the match document with last message info.
        # This avoids N+1 queries in get_conversations.
        await self.matches.update_one(
            {"$or": [
                {"user1_id": sender_id, "user2_id": receiver_id},
                {"user1_id": receiver_id, "user2_id": sender_id},
            ]},
            {"$set": {
                "lastMessage": text[:80],
                "lastMessageAt": now,
                "lastSenderId": sender_id,
            }}
        )

        return msg

    async def get_messages(self, user_id: int, other_user_id: int, after: str = None, limit: int = 50) -> list[dict]:
        """
        Get messages between two users.
        If `after` is provided (ISO timestamp string), only return messages newer than that.
        """
        await self._verify_can_chat(user_id, other_user_id)

        conv_id = self._conversation_id(user_id, other_user_id)
        query = {"conversationId": conv_id}

        if after:
            try:
                after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
                query["sentAt"] = {"$gt": after_dt}
            except (ValueError, TypeError):
                pass

        cursor = self.messages.find(query).sort("sentAt", 1).limit(limit)
        messages = []
        async for msg in cursor:
            msg["_id"] = str(msg["_id"])
            msg["sentAt"] = msg["sentAt"].isoformat() + "Z"
            messages.append(msg)
        return messages

    async def get_conversations(self, user_id: int) -> list[dict]:
        """
        Get a list of conversations for a user with the last message preview.
        Reads denormalized lastMessage fields from match documents instead of
        querying the messages collection per conversation.
        """
        # Single query: get all matches for this user
        match_cursor = self.matches.find({
            "$or": [{"user1_id": user_id}, {"user2_id": user_id}]
        })

        # Collect partner IDs from matches
        matches = []
        partner_ids = []
        async for match in match_cursor:
            partner_id = match["user2_id"] if match["user1_id"] == user_id else match["user1_id"]
            matches.append((match, partner_id))
            partner_ids.append(partner_id)

        # Batch-fetch all partner profiles in one query instead of N queries
        partner_map = {}
        if partner_ids:
            cursor = self.users.find({"id": {"$in": partner_ids}})
            async for p in cursor:
                partner_map[p["id"]] = p

        # Build conversation list from match documents (no messages queries needed)
        conversations = []
        for match, partner_id in matches:
            partner = partner_map.get(partner_id)
            partner_name = partner.get("username", f"User #{partner_id}") if partner else f"User #{partner_id}"
            partner_photo = partner.get("photoUrl", "") if partner else ""

            last_at = match.get("lastMessageAt")
            conv = {
                "partnerId": partner_id,
                "partnerName": partner_name,
                "partnerPhoto": partner_photo,
                "conversationId": self._conversation_id(user_id, partner_id),
                "lastMessage": match.get("lastMessage"),
                "lastMessageAt": last_at.isoformat() + "Z" if last_at else None,
                "lastSenderId": match.get("lastSenderId"),
            }
            conversations.append(conv)

        # Sort by most recent message first
        conversations.sort(
            key=lambda c: c["lastMessageAt"] or "0",
            reverse=True
        )
        return conversations

    async def ensure_indexes(self):
        """Create the compound index for efficient message queries."""
        await self.messages.create_index(
            [("conversationId", 1), ("sentAt", 1)]
        )