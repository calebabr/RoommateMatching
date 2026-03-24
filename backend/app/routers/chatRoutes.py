from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.chatService import ChatService

router = APIRouter()
chatService = ChatService()


class SendMessageRequest(BaseModel):
    receiverId: int
    text: str


@router.post("/chat/{user_id}/send")
async def send_message(user_id: int, request: SendMessageRequest):
    try:
        msg = await chatService.send_message(user_id, request.receiverId, request.text)
        return msg
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chat/{user_id}/messages/{other_user_id}")
async def get_messages(
    user_id: int,
    other_user_id: int,
    after: Optional[str] = Query(None, description="ISO timestamp — only return messages after this time"),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        messages = await chatService.get_messages(user_id, other_user_id, after=after, limit=limit)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chat/{user_id}/conversations")
async def get_conversations(user_id: int):
    try:
        conversations = await chatService.get_conversations(user_id)
        return {"conversations": conversations}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))