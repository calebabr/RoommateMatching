import os
import uuid
import io
import shutil
from datetime import datetime, timezone
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
import cloudinary
import cloudinary.uploader
import httpx
from app.auth.dependencies import get_current_user, get_current_user_or_403, verify_match_exists, get_admin_user
from app.auth.utils import calculate_age
from app.database import (
    users_collection,
    likes_collection,
    matches_collection,
    chat_collection,
    feedback_collection,
    conversation_reports_collection,
    chat_read_status_collection,
    swipes_collection,
)
from app.limiter import limiter
from app.services.userProfileService import UserProfileService
from app.services.recommendationService import RecommendationService
from app.services.likeService import LikeService
from app.services.chatService import ChatService
from app.services.notificationService import NotificationService
from app.services.blockService import BlockService
from app.services.reportService import ReportService
from app.services.deletionService import DeletionService
from app.models import (
    UserCreate,
    UserResponse,
    UserInDB,
    TopMatchesResponse,
    LikeRequest,
    LikeResponse,
    ChatMessageCreate,
    ReportCreate,
    DeleteAccountRequest,
    DeactivateRequest,
    RestoreAccountRequest,
    ResolveReportRequest,
    SubmitAgeRequest,
    AcceptTermsRequest,
    FeedbackCreate,
    ConversationReportCreate,
    ResolveConversationReport,
)

router = APIRouter()

_IMMUTABLE_FIELDS = frozenset({
    "password", "hashed_password", "id", "matched",
    "matchCount", "matchedWith", "createdAt", "email", "photoUrl",
})

userProfileService = UserProfileService()
recommendationService = RecommendationService()
likeService = LikeService()
chatService = ChatService()
notificationService = NotificationService()
blockService = BlockService()
reportService = ReportService()
deletionService = DeletionService()

# --- User CRUD ---

@router.get("/users/all")
@limiter.limit("60/minute")
async def get_all_users(request: Request, _: dict = Depends(get_current_user)):
    cursor = userProfileService.collection.find({"deletedAt": {"$exists": False}})
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
        pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_user(request: Request, user_id: int, _: dict = Depends(get_current_user)):
    try:
        return await userProfileService.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def update_profile(request: Request, user_id: int, user: UserCreate, _: dict = Depends(get_current_user_or_403)):
    try:
        preferences = {k: v for k, v in user.model_dump(exclude_none=True).items()
                       if k not in _IMMUTABLE_FIELDS}
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
@limiter.limit("10/hour")
async def delete_user(request: Request, user_id: int, body: DeleteAccountRequest, _: dict = Depends(get_current_user_or_403)):
    """Soft-delete: marks account for deletion and returns a 7-day restore token."""
    try:
        restore_token = await deletionService.soft_delete_user(user_id, body.password)
        return {
            "message": "Account scheduled for deletion. Use the restore token within 7 days to undo.",
            "restoreToken": restore_token,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Recommendations ---

@router.get("/users/{user_id}/top-matches", response_model=TopMatchesResponse)
@limiter.limit("60/minute")
async def get_top_matches(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    matches = await recommendationService.get_top_matches(user_id)
    if not matches:
        raise HTTPException(status_code=404, detail="No recommendations yet. Run /admin/recompute first.")
    # Filter out blocked, deactivated, paused, and skipped users from recommendations
    blocked_ids = await blockService.get_blocked_ids(user_id)
    skipped_docs = await swipes_collection.find({"user_id": user_id}, {"skipped_user_id": 1}).to_list(length=None)
    skipped_ids = {doc["skipped_user_id"] for doc in skipped_docs}
    excluded_ids = blocked_ids | skipped_ids
    candidate_ids = [m["user_id"] for m in matches if m["user_id"] not in excluded_ids]
    # Exclude deactivated and paused users
    if candidate_ids:
        deactivated_or_paused = await users_collection.find(
            {"id": {"$in": candidate_ids}, "$or": [{"is_deactivated": True}, {"is_paused": True}]},
            {"id": 1}
        ).to_list(length=None)
        hidden_ids = {doc["id"] for doc in deactivated_or_paused}
        excluded_ids = excluded_ids | hidden_ids
    matches = [m for m in matches if m["user_id"] not in excluded_ids]
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
        pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/likes-received")
@limiter.limit("60/minute")
async def get_likes_received(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    likes = await likeService.get_likes_received(user_id)
    blocked_ids = await blockService.get_blocked_ids(user_id)
    # Filter blocked users; also hide likes from paused or deactivated users
    from_user_ids = [like.get("fromUser") for like in likes if like.get("fromUser") not in blocked_ids]
    hidden_ids: set = set()
    if from_user_ids:
        hidden_docs = await users_collection.find(
            {"id": {"$in": from_user_ids}, "$or": [{"is_deactivated": True}, {"is_paused": True}]},
            {"id": 1}
        ).to_list(length=None)
        hidden_ids = {doc["id"] for doc in hidden_docs}
    return [like for like in likes if like.get("fromUser") not in blocked_ids and like.get("fromUser") not in hidden_ids]

@router.get("/users/{user_id}/likes-sent")
@limiter.limit("60/minute")
async def get_likes_sent(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    liked_ids = await likeService.get_likes_sent(user_id)
    blocked_ids = await blockService.get_blocked_ids(user_id)
    return [uid for uid in liked_ids if uid not in blocked_ids]

@router.get("/users/{user_id}/matches")
@limiter.limit("60/minute")
async def get_matches(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    matches = await likeService.get_matches(user_id)
    blocked_ids = await blockService.get_blocked_ids(user_id)
    partner_ids = [
        m["user2_id"] if m["user1_id"] == user_id else m["user1_id"]
        for m in matches
    ]
    # Deactivated users are hidden from everyone including existing matches; paused users still show in matches
    deactivated_ids: set = set()
    if partner_ids:
        deactivated_docs = await users_collection.find(
            {"id": {"$in": partner_ids}, "is_deactivated": True},
            {"id": 1}
        ).to_list(length=None)
        deactivated_ids = {doc["id"] for doc in deactivated_docs}
    filtered = []
    for m in matches:
        partner_id = m["user2_id"] if m["user1_id"] == user_id else m["user1_id"]
        if partner_id not in blocked_ids and partner_id not in deactivated_ids:
            filtered.append(m)
    return filtered

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


# --- P2.29: Cancel a pending like ---

@router.delete("/users/{user_id}/like/{liked_user_id}")
@limiter.limit("30/minute")
async def cancel_like(request: Request, user_id: int, liked_user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Cancel a pending (pre-match) like sent from user_id to liked_user_id."""
    # Check if already matched
    match_doc = await matches_collection.find_one({
        "$or": [
            {"user1_id": user_id, "user2_id": liked_user_id},
            {"user1_id": liked_user_id, "user2_id": user_id},
        ]
    })
    if match_doc:
        raise HTTPException(status_code=409, detail="Cannot cancel a like that has already matched")

    result = await likes_collection.delete_one({"fromUser": user_id, "toUser": liked_user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Like not found")

    return {"message": "Like cancelled"}


# --- P3FT.3: Profile pause ---

@router.post("/users/{user_id}/pause")
@limiter.limit("10/hour")
async def pause_profile(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Pause this user's profile — hides them from discover/recommendations and liked-you lists."""
    result = await users_collection.update_one({"id": user_id}, {"$set": {"is_paused": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Profile paused"}


@router.post("/users/{user_id}/unpause")
@limiter.limit("10/hour")
async def unpause_profile(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Unpause this user's profile — makes them visible in discover again."""
    result = await users_collection.update_one({"id": user_id}, {"$set": {"is_paused": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Profile unpaused"}


# --- P3FT.3: Account deactivation ---

@router.post("/users/{user_id}/deactivate")
@limiter.limit("5/hour")
async def deactivate_account(request: Request, user_id: int, body: DeactivateRequest, _: dict = Depends(get_current_user_or_403)):
    """Deactivate account — profile becomes invisible to everyone until reactivated. Requires password."""
    from app.auth.utils import verify_password
    user = await users_collection.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_pw = user.get("hashed_password", "")
    if not hashed_pw or not verify_password(body.password, hashed_pw):
        raise HTTPException(status_code=400, detail="Incorrect password")

    await users_collection.update_one(
        {"id": user_id},
        {"$set": {"is_deactivated": True, "deactivatedAt": datetime.now(timezone.utc)}},
    )
    return {"message": "Account deactivated"}


@router.post("/users/{user_id}/reactivate")
@limiter.limit("5/hour")
async def reactivate_account(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Reactivate a previously deactivated account."""
    result = await users_collection.update_one(
        {"id": user_id},
        {"$set": {"is_deactivated": False}, "$unset": {"deactivatedAt": ""}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Account reactivated"}


# --- P3FT.4: Skip/pass ---

@router.post("/users/{user_id}/skip/{skipped_user_id}")
@limiter.limit("60/minute")
async def skip_user(request: Request, user_id: int, skipped_user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Record that user_id has skipped/passed on skipped_user_id. TTL = 30 days."""
    if user_id == skipped_user_id:
        raise HTTPException(status_code=400, detail="Cannot skip yourself")

    await swipes_collection.update_one(
        {"user_id": user_id, "skipped_user_id": skipped_user_id},
        {"$set": {"user_id": user_id, "skipped_user_id": skipped_user_id, "skipped_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"message": "Skipped"}


# --- Block ---

@router.post("/users/{user_id}/block")
@limiter.limit("60/minute")
async def block_user(request: Request, user_id: int, body: dict, _: dict = Depends(get_current_user_or_403)):
    """Block another user. Auto-unmatches the pair and removes pending likes."""
    blocked_id = body.get("userId")
    if not isinstance(blocked_id, int):
        raise HTTPException(status_code=422, detail="userId (int) required in body")
    try:
        await blockService.block_user(user_id, blocked_id)
        return {"message": "User blocked"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/{user_id}/unblock")
@limiter.limit("60/minute")
async def unblock_user(request: Request, user_id: int, body: dict, _: dict = Depends(get_current_user_or_403)):
    """Unblock a previously blocked user. Does not restore any prior match."""
    blocked_id = body.get("userId")
    if not isinstance(blocked_id, int):
        raise HTTPException(status_code=422, detail="userId (int) required in body")
    await blockService.unblock_user(user_id, blocked_id)
    return {"message": "User unblocked"}


@router.get("/users/{user_id}/blocked")
@limiter.limit("60/minute")
async def get_blocked_users(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Return list of users explicitly blocked by this user."""
    return await blockService.get_blocked_by_user(user_id)


# --- Report ---

@router.post("/users/{user_id}/report/{reported_id}")
@limiter.limit("5/day")
async def report_user_by_id(
    request: Request,
    user_id: int,
    reported_id: int,
    body: ReportCreate,
    _: dict = Depends(get_current_user_or_403),
):
    """Report a specific user. Automatically blocks the reported user from seeing the reporter."""
    try:
        report = await reportService.create_report(
            reporter_id=user_id,
            reported_id=reported_id,
            reason=body.reason.value,
            description=body.description,
        )
        # Block in reporter → reported direction so reported user can't see reporter
        await blockService.block_user(user_id, reported_id)
        return {"message": "Report submitted", "reportId": report["id"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Data Export ---

@router.get("/users/{user_id}/export")
@limiter.limit("5/hour")
async def export_user_data(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Export all data associated with this user account."""
    try:
        return await deletionService.export_user_data(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Age Verification ---

@router.post("/users/{user_id}/submit-age")
@limiter.limit("5/hour")
async def submit_age(
    request: Request,
    user_id: int,
    body: SubmitAgeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit date of birth for existing users who registered before age verification was added."""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        age = calculate_age(body.dateOfBirth)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dateOfBirth format. Use YYYY-MM-DD.")

    if age < 18:
        await users_collection.update_one(
            {"id": user_id},
            {"$set": {
                "is_banned": True,
                "ban_reason": "Account suspended: you must be at least 18 years old.",
            }},
        )
        return {
            "status": "banned",
            "message": "Your account has been suspended because you do not meet the minimum age requirement of 18 years.",
        }

    await users_collection.update_one(
        {"id": user_id},
        {"$set": {"dateOfBirth": body.dateOfBirth}},
    )
    return {"status": "ok"}


# --- Terms of Service ---

@router.post("/users/{user_id}/accept-terms")
@limiter.limit("10/hour")
async def accept_terms(
    request: Request,
    user_id: int,
    body: AcceptTermsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record that the user has accepted the specified version of the Terms of Service."""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await users_collection.update_one(
        {"id": user_id},
        {"$set": {
            "termsVersion": body.termsVersion,
            "termsAcceptedAt": datetime.utcnow().isoformat(),
        }},
    )
    return {"status": "ok"}


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
        messages = await chatService.get_messages(user_id, partner_id, limit)
        # Look up when the PARTNER last read this conversation
        partner_read_status = await chat_read_status_collection.find_one(
            {"user_id": partner_id, "partner_id": user_id}
        )
        partner_last_read_at = partner_read_status["last_read_at"] if partner_read_status else None
        return {"messages": messages, "partner_last_read_at": partner_last_read_at}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Chat Read Receipts ---

@router.post("/chat/{partner_id}/mark-read")
@limiter.limit("60/minute")
async def mark_chat_read(request: Request, partner_id: int, current_user: dict = Depends(get_current_user)):
    """Mark a conversation with a partner as read up to now."""
    user_id = current_user["id"]
    await chat_read_status_collection.update_one(
        {"user_id": user_id, "partner_id": partner_id},
        {"$set": {"user_id": user_id, "partner_id": partner_id, "last_read_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"status": "ok"}


@router.get("/users/{user_id}/unread-chats")
@limiter.limit("60/minute")
async def get_unread_chats(request: Request, user_id: int, _: dict = Depends(get_current_user_or_403)):
    """Return unread chat count and list of partner IDs with unread messages."""
    # Get all match partner IDs for this user
    match_docs = await matches_collection.find(
        {"$or": [{"user1_id": user_id}, {"user2_id": user_id}]}
    ).to_list(length=None)
    partner_ids = [
        doc["user2_id"] if doc["user1_id"] == user_id else doc["user1_id"]
        for doc in match_docs
    ]

    unread_partner_ids = []
    for partner_id in partner_ids:
        read_status = await chat_read_status_collection.find_one(
            {"user_id": user_id, "partner_id": partner_id}
        )
        query = {"fromUser": partner_id, "toUser": user_id}
        if read_status:
            query["createdAt"] = {"$gt": read_status["last_read_at"]}
        count = await chat_collection.count_documents(query)
        if count > 0:
            unread_partner_ids.append(partner_id)

    return {"unread_count": len(unread_partner_ids), "unread_partner_ids": unread_partner_ids}


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

# Configure Cloudinary at module load time from environment variables
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.environ.get("CLOUDINARY_API_KEY", ""),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET", ""),
)


def _detect_image_type(data: bytes) -> str | None:
    """Inspect raw bytes to identify image format. Returns 'jpeg', 'png', 'webp', or None."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a":
        return "png"
    if data[:4] == b"\x52\x49\x46\x46" and data[8:12] == b"\x57\x45\x42\x50":
        return "webp"
    return None


def _reencode_image(data: bytes, fmt: str) -> bytes:
    """Re-encode image via Pillow to strip EXIF/metadata and neutralize payloads."""
    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    pil_format = {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[fmt]
    img.save(buf, format=pil_format)
    return buf.getvalue()


@router.post("/users/{user_id}/upload-photo")
@limiter.limit("10/hour")
async def upload_photo(request: Request, user_id: int, file: UploadFile = File(...), _: dict = Depends(get_current_user_or_403)):
    """Upload a profile photo. Validates, re-encodes, uploads to Cloudinary, stores URL in user profile."""
    # Validate user exists
    try:
        user = await userProfileService.get_user(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    # Read file contents
    contents = await file.read()

    # Enforce 5MB size limit (413 Request Entity Too Large)
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 5MB.")

    # Validate format via magic bytes — never trust Content-Type header
    fmt = _detect_image_type(contents)
    if fmt is None:
        raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, or WebP)")

    # Dimension validation — do this before re-encoding to avoid processing huge images
    try:
        img_check = Image.open(io.BytesIO(contents))
        width, height = img_check.size
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image dimensions")

    if width < 100 or height < 100:
        raise HTTPException(status_code=400, detail="Image too small (min 100x100)")
    if width > 4000 or height > 4000:
        raise HTTPException(status_code=400, detail="Image too large (max 4000x4000)")

    # Re-encode via Pillow: strips EXIF (GPS, etc.) and neutralizes embedded payloads
    reencoded_bytes = _reencode_image(contents, fmt)

    # Generate UUID-based filename — never use user-provided extension
    ext_map = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}
    uuid_stem = str(uuid.uuid4())
    filename = uuid_stem + ext_map[fmt]

    # Delete old photo if it exists
    old_url = user.get("photoUrl", "")
    if old_url:
        if "cloudinary.com" in old_url:
            # Extract public_id from Cloudinary URL (everything after last '/' minus extension)
            try:
                old_public_id = old_url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                cloudinary.uploader.destroy(old_public_id)
            except Exception:
                pass  # Non-fatal: old photo deletion failure should not block new upload
        elif "/uploads/" in old_url:
            # Legacy local file — backwards compat for existing users
            old_filename = old_url.split("/uploads/")[-1]
            old_path = os.path.join(UPLOAD_DIR, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)

    # Upload re-encoded bytes to Cloudinary
    result = cloudinary.uploader.upload(
        reencoded_bytes,
        public_id=uuid_stem,
        resource_type="image",
        overwrite=True,
    )
    photo_url = result["secure_url"]

    # Persist Cloudinary URL in the user's profile
    await userProfileService.collection.update_one(
        {"id": user_id},
        {"$set": {"photoUrl": photo_url}}
    )

    return {"photoUrl": photo_url, "filename": filename}

# --- Admin ---

@router.get("/admin/users")
@limiter.limit("30/minute")
async def admin_list_users(request: Request, include_deleted: bool = False, _: dict = Depends(get_admin_user)):
    query = {} if include_deleted else {"deletedAt": {"$exists": False}}
    cursor = userProfileService.collection.find(query)
    users = []
    async for user in cursor:
        user.pop("_id", None)
        user.pop("hashed_password", None)
        users.append(user)
    return users


@router.post("/admin/ban/{user_id}")
async def ban_user(user_id: int, _: dict = Depends(get_admin_user)):
    result = await userProfileService.collection.update_one({"id": user_id}, {"$set": {"is_banned": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User banned"}


@router.post("/admin/unban/{user_id}")
async def unban_user(user_id: int, _: dict = Depends(get_admin_user)):
    result = await userProfileService.collection.update_one({"id": user_id}, {"$set": {"is_banned": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User unbanned"}


@router.post("/admin/recompute")
@limiter.limit("60/minute")
async def recompute_all(request: Request, _: dict = Depends(get_admin_user)):
    users = await userProfileService.get_all_active_users()
    if len(users) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 active users")

    user_dicts = []
    for u in users:
        user_in_db = UserInDB(**u)
        user_dicts.append(user_in_db.toMatchDict())

    await recommendationService.recompute_all(user_dicts)
    return {"message": f"Recomputed recommendations for {len(users)} users"}


@router.get("/admin/users/{user_id}/activity")
@limiter.limit("30/minute")
async def admin_user_activity(request: Request, user_id: int, _: dict = Depends(get_admin_user)):
    user = await users_collection.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    async def get_username(uid: int) -> str:
        u = await users_collection.find_one({"id": uid})
        return u.get("username", f"User #{uid}") if u else "Deleted User"

    # Matches
    match_docs = await matches_collection.find(
        {"$or": [{"user1_id": user_id}, {"user2_id": user_id}]}
    ).to_list(length=None)
    matches = []
    for doc in match_docs:
        partner_id = doc["user2_id"] if doc["user1_id"] == user_id else doc["user1_id"]
        matches.append({
            "partner_id": partner_id,
            "partner_name": await get_username(partner_id),
            "matched_date": doc.get("confirmedAt"),
        })

    # Likes sent
    like_docs = await likes_collection.find({"fromUser": user_id}).to_list(length=None)
    likes_sent = []
    for doc in like_docs:
        to_id = doc["toUser"]
        likes_sent.append({
            "to_user_id": to_id,
            "to_user_name": await get_username(to_id),
            "created_at": doc.get("createdAt"),
        })

    # Chat partners — find all unique partners and aggregate per-conversation stats
    sent_msgs = await chat_collection.find({"fromUser": user_id}).to_list(length=None)
    received_msgs = await chat_collection.find({"toUser": user_id}).to_list(length=None)

    partner_ids = set()
    for msg in sent_msgs + received_msgs:
        other = msg["toUser"] if msg["fromUser"] == user_id else msg["fromUser"]
        partner_ids.add(other)

    chat_partners = []
    for partner_id in partner_ids:
        conversation = [
            m for m in sent_msgs + received_msgs
            if (m["fromUser"] == user_id and m["toUser"] == partner_id)
            or (m["fromUser"] == partner_id and m["toUser"] == user_id)
        ]
        message_count = len(conversation)
        last_ts = max((m["createdAt"] for m in conversation if m.get("createdAt")), default=None)
        chat_partners.append({
            "partner_id": partner_id,
            "partner_name": await get_username(partner_id),
            "message_count": message_count,
            "last_message_at": last_ts,
        })

    return {
        "matches": matches,
        "likes_sent": likes_sent,
        "chat_partners": chat_partners,
    }


@router.get("/admin/reports")
@limiter.limit("30/minute")
async def admin_get_reports(request: Request, status: str = None, _: dict = Depends(get_admin_user)):
    """Admin endpoint: list all reports, optionally filtered by status (pending/actioned/dismissed)."""
    return await reportService.get_reports(status_filter=status)


@router.post("/admin/reports/{report_id}/resolve")
@limiter.limit("30/minute")
async def admin_resolve_report(request: Request, report_id: str, body: ResolveReportRequest, current_admin: dict = Depends(get_admin_user)):
    """Admin endpoint: resolve a report as actioned or dismissed."""
    try:
        result = await reportService.resolve_report(
            report_id=report_id,
            admin_id=current_admin["id"],
            resolution=body.resolution,
            status=body.status,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- P3AD.1: Sentry Error Proxy ---

@router.get("/admin/errors")
@limiter.limit("30/minute")
async def admin_sentry_errors(request: Request, _: dict = Depends(get_admin_user)):
    """Proxy recent Sentry issues to the admin dashboard."""
    sentry_token = os.environ.get("SENTRY_AUTH_TOKEN")
    sentry_org = os.environ.get("SENTRY_ORG")
    sentry_project = os.environ.get("SENTRY_PROJECT")

    if not all([sentry_token, sentry_org, sentry_project]):
        return {"error": "Sentry not configured", "issues": []}

    url = f"https://sentry.io/api/0/projects/{sentry_org}/{sentry_project}/issues/?limit=25&statsPeriod=7d"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {sentry_token}"})
            response.raise_for_status()
            return {"issues": response.json()}
    except Exception as e:
        return {"error": str(e), "issues": []}


# --- P3AD.2: User Feedback ---

@router.post("/feedback")
@limiter.limit("10/hour")
async def submit_feedback(request: Request, body: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    """Submit user feedback."""
    doc = {
        "user_id": current_user["id"],
        "message": body.message,
        "createdAt": datetime.utcnow().isoformat(),
    }
    await feedback_collection.insert_one(doc)
    return {"status": "ok"}


@router.get("/admin/feedback")
@limiter.limit("60/minute")
async def admin_get_feedback(request: Request, _: dict = Depends(get_admin_user)):
    """Admin endpoint: list all user feedback with usernames, sorted newest first."""
    cursor = feedback_collection.find({}, {"_id": 0}).sort("createdAt", -1)
    items = []
    async for doc in cursor:
        user = await users_collection.find_one({"id": doc.get("user_id")})
        doc["username"] = user.get("username", f"User #{doc.get('user_id')}") if user else "Deleted User"
        items.append(doc)
    return {"feedback": items}


# --- P3AD.4: Reported Conversation Moderation ---

@router.post("/chat/{partner_id}/report")
@limiter.limit("5/hour")
async def report_conversation(
    request: Request,
    partner_id: int,
    body: ConversationReportCreate,
    current_user: dict = Depends(get_current_user),
):
    """Report a chat conversation with a matched partner."""
    user_id = current_user["id"]

    # Verify a match exists between current user and partner
    match_doc = await matches_collection.find_one({
        "$or": [
            {"user1_id": user_id, "user2_id": partner_id},
            {"user1_id": partner_id, "user2_id": user_id},
        ]
    })
    if not match_doc:
        raise HTTPException(status_code=403, detail="You are not matched with this user")

    doc = {
        "reporter_id": user_id,
        "reported_user_id": partner_id,
        "reason": body.reason,
        "status": "pending",
        "createdAt": datetime.utcnow().isoformat(),
    }
    await conversation_reports_collection.insert_one(doc)
    return {"status": "ok"}


@router.get("/admin/conversation-reports")
@limiter.limit("60/minute")
async def admin_get_conversation_reports(request: Request, _: dict = Depends(get_admin_user)):
    """Admin endpoint: list all pending conversation reports with usernames."""
    cursor = conversation_reports_collection.find({"status": "pending"}).sort("createdAt", -1)
    reports = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        reporter = await users_collection.find_one({"id": doc.get("reporter_id")})
        reported = await users_collection.find_one({"id": doc.get("reported_user_id")})
        doc["reporter_username"] = reporter.get("username", f"User #{doc.get('reporter_id')}") if reporter else "Deleted User"
        doc["reported_username"] = reported.get("username", f"User #{doc.get('reported_user_id')}") if reported else "Deleted User"
        reports.append(doc)
    return {"reports": reports}


@router.get("/admin/conversation-reports/{report_id}/messages")
@limiter.limit("60/minute")
async def admin_get_report_messages(request: Request, report_id: str, _: dict = Depends(get_admin_user)):
    """Admin endpoint: fetch full chat history for a reported conversation."""
    from bson import ObjectId
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_id")

    report = await conversation_reports_collection.find_one({"_id": oid})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    reporter_id = report["reporter_id"]
    reported_user_id = report["reported_user_id"]

    cursor = chat_collection.find({
        "$or": [
            {"fromUser": reporter_id, "toUser": reported_user_id},
            {"fromUser": reported_user_id, "toUser": reporter_id},
        ]
    }).sort("createdAt", 1)

    messages = []
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])
        messages.append(msg)
    return {"messages": messages}


@router.post("/admin/conversation-reports/{report_id}/resolve")
@limiter.limit("60/minute")
async def admin_resolve_conversation_report(
    request: Request,
    report_id: str,
    body: ResolveConversationReport,
    _: dict = Depends(get_admin_user),
):
    """Admin endpoint: resolve a conversation report (dismiss or ban reported user)."""
    from bson import ObjectId
    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report_id")

    report = await conversation_reports_collection.find_one({"_id": oid})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if body.action == "ban":
        await users_collection.update_one(
            {"id": report["reported_user_id"]},
            {"$set": {"is_banned": True}},
        )

    await conversation_reports_collection.update_one(
        {"_id": oid},
        {"$set": {"status": "resolved"}},
    )
    return {"status": "ok"}

