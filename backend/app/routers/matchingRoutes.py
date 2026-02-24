from fastapi import APIRouter, HTTPException, UploadFile, File
import json

from app.services.matchScore import matchScore
from app.services.matchingUsers import matchingUsers
from app.services.userProfileService import UserProfileService
from app.models import (
    UserInDB,
    UserDB,
    MatchScoreRequest,
    MatchResult,
    MatchListResult,
)

router = APIRouter()
matchScoreCalculator = matchScore()
matchingService = matchingUsers()
userProfileService = UserProfileService()

@router.post("/matchScore", response_model=MatchResult)
async def calculateMatchScore(request: MatchScoreRequest):
    try:
        user1 = await userProfileService.get_user(request.user1_id)
        user2 = await userProfileService.get_user(request.user2_id)

        user1_dict = UserInDB(**user1).toMatchDict()
        user2_dict = UserInDB(**user2).toMatchDict()

        score = matchScoreCalculator.compatibilityScore(user1_dict, user2_dict)
        return MatchResult(user1_id=request.user1_id, user2_id=request.user2_id, compatibilityScore=score)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/uploadUsers")
async def upload_users(file: UploadFile = File(...)):
    contents = await file.read()
    data = json.loads(contents)

    for user_data in data["users"]:
        try:
            await userProfileService.create_user(user_data)
        except ValueError:
            continue

    return {"message": f"Uploaded {len(data['users'])} users"}

@router.post("/match", response_model=MatchListResult)
async def find_all_matches():
    users = await userProfileService.get_all_active_users()
    if len(users) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 active users")

    user_dicts = []
    for u in users:
        user_in_db = UserInDB(**u)
        user_dicts.append(user_in_db.toMatchDict())

    matches = matchingService.find_matches(user_dicts)
    return matches
