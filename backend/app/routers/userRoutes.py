import os
import uuid
import io
import shutil
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
import cloudinary
import cloudinary.uploader
from app.auth.dependencies import get_current_user, get_current_user_or_403, verify_match_exists, get_admin_user
from app.database import users_collection, likes_collection, matches_collection, chat_collection
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
    RestoreAccountRequest,
    ResolveReportRequest,
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
    # Filter out blocked users and soft-deleted users from recommendations
    blocked_ids = await blockService.get_blocked_ids(user_id)
    matches = [m for m in matches if m["user_id"] not in blocked_ids]
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
    return [like for like in likes if like.get("fromUser") not in blocked_ids]

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
    filtered = []
    for m in matches:
        partner_id = m["user2_id"] if m["user1_id"] == user_id else m["user1_id"]
        if partner_id not in blocked_ids:
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