import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from app.auth.dependencies import get_current_user, get_current_user_or_403, verify_match_exists
from app.limiter import limiter
from app.services.userProfileService import UserProfileService
from app.services.recommendationService import RecommendationService
from app.services.likeService import LikeService
from app.services.chatService import ChatService
from app.services.notificationService import NotificationService
from app.models import (
    UserCreate,
    UserResponse,
    UserInDB,
    TopMatchesResponse,
    LikeRequest,
    LikeResponse,
    ChatMessageCreate,
)

router = APIRouter()

userProfileService = UserProfileService()
recommendationService = RecommendationService()
likeService = LikeService()
chatService = ChatService()
notificationService = NotificationService()

# --- User CRUD ---

@router.get("/users/all")
@limiter.limit("60/minute")
async def get_all_users(request: Request, _: dict = Depends(get_current_user)):
    cursor = userProfileService.collection.find({})
    users = []
    async for user in cursor:
        user.pop("_id", None)
        user.pop("hashed_password", None)
        users.append(user)
    return users

@router.post("/users", response_model=UserResponse)
@limiter.limit("60/minute")
async def create_user(request: Request, user: UserCreate, _: dict = Depends(get_current_user)):
    try:
        user_data = user.model_dump()
        # Validate gender
        if user_data.get("gender", "").lower() not in ("male", "female"):
            raise ValueError("Gender must be 'male' or 'female'")
        user_data["gender"] = user_data["gender"].lower()
        result = await userProfileService.create_user(user_data)

        # Auto-recompute for this user
        users = await userProfileService.get_all_active_users()
        if len(users) >= 2:
            user_dicts = [UserInDB(**u).toMatchDict() for u in users]
            new_user_dict = UserInDB(**result).toMatchDict()
            await recommendationService.on_new_user(new_user_dict, user_dicts)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_user(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    try:
        return await userProfileService.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def update_profile(request: Request, user_id: int, user: UserCreate, _: dict = Depends(get_current_user_or_403)):
    try:
        preferences = user.model_dump(exclude_none=True)
        result = await userProfileService.update_profile(user_id, preferences)

        # Recompute recommendations with new preferences
        users = await userProfileService.get_all_active_users()
        if len(users) >= 2:
            user_dicts = [UserInDB(**u).toMatchDict() for u in users]
            updated_dict = UserInDB(**result).toMatchDict()
            await recommendationService.on_new_user(updated_dict, user_dicts)

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}")
@limiter.limit("60/minute")
async def delete_user(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    deleted = await userProfileService.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

# --- Recommendations ---

@router.get("/users/{user_id}/top-matches", response_model=TopMatchesResponse)
@limiter.limit("60/minute")
async def get_top_matches(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    matches = await recommendationService.get_top_matches(user_id)
    if not matches:
        raise HTTPException(status_code=404, detail="No recommendations yet. Run /admin/recompute first.")
    return TopMatchesResponse(userId=user_id, matches=matches)

# --- Likes and Matching ---

@router.post("/users/{user_id}/like", response_model=LikeResponse)
@limiter.limit("100/hour")
async def like_user(request: Request, user_id: int, body: LikeRequest, _: dict = Depends(get_current_user_or_403)):
    try:
        result = await likeService.send_like(user_id, body.toUser)
        return LikeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/likes-received")
@limiter.limit("60/minute")
async def get_likes_received(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    return await likeService.get_likes_received(user_id)

@router.get("/users/{user_id}/likes-sent")
@limiter.limit("60/minute")
async def get_likes_sent(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    return await likeService.get_likes_sent(user_id)

@router.get("/users/{user_id}/matches")
@limiter.limit("60/minute")
async def get_matches(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    return await likeService.get_matches(user_id)

@router.post("/users/{user_id}/unmatch/{partner_id}")
@limiter.limit("60/minute")
async def unmatch_user(request: Request, user_id: int, partner_id: int, _: dict = Depends(get_current_user_or_403)):
    try:
        result = await likeService.unmatch(user_id, partner_id)

        users = await userProfileService.get_all_active_users()
        if len(users) >= 2:
            user_dicts = [UserInDB(**u).toMatchDict() for u in users]
            await recommendationService.on_user_unmatched(result["unmatched_user"], user_dicts)
            await recommendationService.on_user_unmatched(result["was_matched_with"], user_dicts)

        return {"message": "Unmatched successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Chat ---

@router.get("/users/{user_id}/chat/conversations")
@limiter.limit("60/minute")
async def get_conversations(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    try:
        return await chatService.get_conversations(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/users/{user_id}/chat/{partner_id}")
@limiter.limit("30/minute")
async def send_chat_message(request: Request, user_id: int, partner_id: int, message: ChatMessageCreate, _: dict = Depends(get_current_user_or_403), __: None = Depends(verify_match_exists)):
    try:
        result = await chatService.send_message(user_id, partner_id, message.content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}/chat/{partner_id}")
@limiter.limit("60/minute")
async def get_chat_messages(request: Request, user_id: int, partner_id: int, limit: int = 100, _: dict = Depends(get_current_user_or_403), __: None = Depends(verify_match_exists)):
    try:
        return await chatService.get_messages(user_id, partner_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Notifications ---

@router.get("/users/{user_id}/notifications")
@limiter.limit("60/minute")
async def get_notifications(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    return await notificationService.get_notifications(user_id)

@router.get("/users/{user_id}/notifications/unread-count")
@limiter.limit("60/minute")
async def get_unread_count(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    count = await notificationService.get_unread_count(user_id)
    return {"count": count}

@router.post("/users/{user_id}/notifications/mark-read")
@limiter.limit("60/minute")
async def mark_all_notifications_read(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    count = await notificationService.mark_all_read(user_id)
    return {"marked": count}

# --- Photo Upload ---

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/users/{user_id}/upload-photo")
@limiter.limit("10/hour")
async def upload_photo(request: Request, user_id: int, file: UploadFile = File(...), _: dict = Depends(get_current_user_or_403)):
    """Upload a profile photo. Saves to disk, stores URL in user profile."""
    # Validate user exists
    try:
        user = await userProfileService.get_user(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, WebP, or GIF)")

    # Limit file size (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Delete old photo if exists
    old_url = user.get("photoUrl", "")
    if old_url and "/uploads/" in old_url:
        old_filename = old_url.split("/uploads/")[-1]
        old_path = os.path.join(UPLOAD_DIR, old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new file
    with open(filepath, "wb") as f:
        f.write(contents)

    # Store the relative URL in user profile
    photo_url = f"/uploads/{filename}"
    await userProfileService.collection.update_one(
        {"id": user_id},
        {"$set": {"photoUrl": photo_url}}
    )

    return {"photoUrl": photo_url, "filename": filename}

# --- Admin ---

@router.post("/admin/recompute")
@limiter.limit("60/minute")
async def recompute_all(request: Request, _: dict = Depends(get_current_user)):
    users = await userProfileService.get_all_active_users()
    if len(users) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 active users")

    user_dicts = []
    for u in users:
        user_in_db = UserInDB(**u)
        user_dicts.append(user_in_db.toMatchDict())

    await recommendationService.recompute_all(user_dicts)
    return {"message": f"Recomputed recommendations for {len(users)} users"}