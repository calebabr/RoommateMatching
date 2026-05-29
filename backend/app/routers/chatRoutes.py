from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.services.chatService import ChatService
from app.auth.dependencies import get_current_user_or_403, verify_match_exists
from app.database import matches_collection

router = APIRouter()
chatService = ChatService()


class SendMessageRequest(BaseModel):
    receiverId: int
    text: str


@router.post("/chat/{user_id}/send")
async def send_message(
    user_id: int,
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user_or_403),
):
    match = await matches_collection.find_one({
        "$or": [
            {"user1_id": user_id, "user2_id": request.receiverId},
            {"user1_id": request.receiverId, "user2_id": user_id},
        ]
    })
    if match is None:
        raise HTTPException(status_code=403, detail="Not matched with this user")
    try:
        msg = await chatService.send_message(user_id, request.receiverId, request.text)
        return msg
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# partner_id path param name matches verify_match_exists dependency signature
@router.get("/chat/{user_id}/messages/{partner_id}")
async def get_messages(
    user_id: int,
    partner_id: int,
    after: Optional[str] = Query(None, description="ISO timestamp — only return messages after this time"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user_or_403),
    _match: None = Depends(verify_match_exists),
):
    try:
        messages = await chatService.get_messages(user_id, partner_id, after=after, limit=limit)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chat/{user_id}/conversations")
async def get_conversations(
    user_id: int,
    current_user: dict = Depends(get_current_user_or_403),
):
    try:
        conversations = await chatService.get_conversations(user_id)
        return {"conversations": conversations}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
