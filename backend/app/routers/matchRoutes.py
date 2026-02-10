from fastapi import APIRouter, HTTPException, UploadFile, File
import json

from app.services.matchScore import matchScore
from app.services.matchingUsers import matchingUsers

from app.models import(
    Preference,
    User,
    MatchScoreRequest,
    MatchResult,
    MatchListResult,
    UserDB
)
router = APIRouter()
matchScoreCalculator = matchScore()
matchingService = matchingUsers()

userStore = {"users: ": None}

@router.post("/uploadUsers")
async def upload_users(file: UploadFile = File(...)):
    contents = await file.read()
    data = json.loads(contents)
    userDB = UserDB(**data)
    userStore["users"] = userDB
    return {"message": f"Uploaded {len(userDB.users)} users"}

@router.get("/get-users")
async def get_users():
    if userStore["users"] is None:
        raise HTTPException(status_code=400, detail="No users uploaded. Use /uploadUsers first.")
    return userStore["users"].toDict()

@router.post("/match", response_model=MatchListResult)
async def find_all_matches():
    if userStore["users"] is None:
        raise HTTPException(status_code=400, detail="No users uploaded. Use /uploadUsers first.")

    user_dicts = [u.toDict() for u in userStore["users"].users]
    matches = matchingService.find_matches(user_dicts)
    return matches

@router.post("/matchScore", response_model=MatchResult)
async def calculateMatchScore(request: MatchScoreRequest) -> MatchResult:
    if userStore["users"] is None:
        raise HTTPException(status_code=400, detail="No users uploaded. Use /uploadUsers first.")

    user1 = None
    user2 = None
    for u in userStore["users"].users:
        if u.id == request.user1_id:
            user1 = u
        if u.id == request.user2_id:
            user2 = u

    if not user1 or not user2:
        raise HTTPException(status_code=404, detail="User not found")

    score = matchScoreCalculator.compatibilityScore(user1.toDict(), user2.toDict())
    return MatchResult(user1_id=user1.id, user2_id=user2.id, compatibilityScore=score)