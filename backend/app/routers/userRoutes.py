import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.userProfileService import UserProfileService
from app.services.recommendationService import RecommendationService
from app.services.likeService import LikeService
from app.models import (
    UserCreate,
    UserResponse,
    UserInDB,
    TopMatchesResponse,
    LikeRequest,
    LikeResponse,
)

router = APIRouter()

userProfileService = UserProfileService()
recommendationService = RecommendationService()
likeService = LikeService()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "photos")

# --- User CRUD ---

@router.get("/users/all")
async def get_all_users():
    cursor = userProfileService.collection.find({})
    users = []
    async for user in cursor:
        user.pop("_id", None)
        users.append(user)
    return users

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    try:
        user_data = user.model_dump()
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
async def get_user(user_id: int):
    try:
        return await userProfileService.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_profile(user_id: int, user: UserCreate):
    try:
        preferences = user.model_dump()
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
async def delete_user(user_id: int):
    # Clean up photo file if it exists
    try:
        user = await userProfileService.get_user(user_id)
        photo_url = user.get("photoUrl", "")
        if photo_url and photo_url.startswith("/uploads/photos/"):
            filename = photo_url.split("/")[-1]
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    except Exception:
        pass

    deleted = await userProfileService.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

# --- Photo Upload ---

@router.post("/users/{user_id}/photo")
async def upload_photo(user_id: int, file: UploadFile = File(...)):
    # Validate user exists
    try:
        user = await userProfileService.get_user(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp", "image/heic"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed. Use JPEG, PNG, or WebP.")

    # Limit file size (5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    # Delete old photo if exists
    old_url = user.get("photoUrl", "")
    if old_url and old_url.startswith("/uploads/photos/"):
        old_file = os.path.join(UPLOAD_DIR, old_url.split("/")[-1])
        if os.path.exists(old_file):
            os.remove(old_file)

    # Save new photo
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # Update user record with the photo path
    photo_path = f"/uploads/photos/{filename}"
    await userProfileService.collection.find_one_and_update(
        {"id": user_id},
        {"$set": {"photoUrl": photo_path}}
    )

    return {"photoUrl": photo_path}

@router.delete("/users/{user_id}/photo")
async def delete_photo(user_id: int):
    try:
        user = await userProfileService.get_user(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    photo_url = user.get("photoUrl", "")
    if photo_url and photo_url.startswith("/uploads/photos/"):
        filename = photo_url.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    await userProfileService.collection.find_one_and_update(
        {"id": user_id},
        {"$set": {"photoUrl": ""}}
    )

    return {"message": "Photo removed"}

# --- Recommendations ---

@router.get("/users/{user_id}/top-matches", response_model=TopMatchesResponse)
async def get_top_matches(user_id: int):
    matches = await recommendationService.get_top_matches(user_id)
    if not matches:
        raise HTTPException(status_code=404, detail="No recommendations yet. Run /admin/recompute first.")
    return TopMatchesResponse(userId=user_id, matches=matches)

# --- Likes and Matching ---

@router.post("/users/{user_id}/like", response_model=LikeResponse)
async def like_user(user_id: int, request: LikeRequest):
    try:
        result = await likeService.send_like(user_id, request.toUser)
        return LikeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{user_id}/likes-received")
async def get_likes_received(user_id: int):
    return await likeService.get_likes_received(user_id)

@router.get("/users/{user_id}/matches")
async def get_matches(user_id: int):
    return await likeService.get_matches(user_id)

@router.post("/users/{user_id}/unmatch")
async def unmatch_user(user_id: int):
    try:
        result = await likeService.unmatch(user_id)

        # Recompute recommendations for both users
        users = await userProfileService.get_all_active_users()
        if len(users) >= 2:
            user_dicts = [UserInDB(**u).toMatchDict() for u in users]
            await recommendationService.on_user_unmatched(result["unmatched_user"], user_dicts)
            if result["was_matched_with"]:
                await recommendationService.on_user_unmatched(result["was_matched_with"], user_dicts)

        return {"message": "Unmatched successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Admin ---

@router.post("/admin/recompute")
async def recompute_all():
    users = await userProfileService.get_all_active_users()
    if len(users) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 active users")

    user_dicts = []
    for u in users:
        user_in_db = UserInDB(**u)
        user_dicts.append(user_in_db.toMatchDict())

    await recommendationService.recompute_all(user_dicts)
    return {"message": f"Recomputed recommendations for {len(users)} users"}