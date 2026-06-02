import os
import uuid
import io
import shutil
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
import cloudinary
import cloudinary.uploader
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

_IMMUTABLE_FIELDS = frozenset({
    "password", "hashed_password", "id", "matched",
    "matchCount", "matchedWith", "createdAt", "email",
})

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
        pass
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