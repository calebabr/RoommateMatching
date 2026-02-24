from fastapi import APIRouter, HTTPException
from app.services.userProfileService import UserProfileService
from app.services.clusterService import ClusterService
from app.services.recommendationService import RecommendationService
from app.services.likeService import LikeService
from app.models import (
    UserCreate,
    UserResponse,
    UserInDB,
    TopMatchesResponse,
    LikeRequest,
    LikeResponse,
    MatchResult,
)

router = APIRouter()

userProfileService = UserProfileService()
clusterService = ClusterService()
recommendationService = RecommendationService(clusterService)
likeService = LikeService()

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
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        return await userProfileService.update_profile(user_id, preferences)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    deleted = await userProfileService.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

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

        if result["status"] == "matched":
            await userProfileService.mark_matched(user_id, request.toUser)
            await userProfileService.mark_matched(request.toUser, user_id)
            await recommendationService.on_user_matched(user_id)
            await recommendationService.on_user_matched(request.toUser)

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
        user = await userProfileService.get_user(user_id)
        matched_with = user.get("matchedWith")

        await userProfileService.unmatch_user(user_id)
        if matched_with:
            await userProfileService.unmatch_user(matched_with)

        return {"message": "Unmatched successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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