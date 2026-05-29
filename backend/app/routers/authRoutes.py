from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import users_collection
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    gender: Optional[str] = ""
    bio: Optional[str] = ""
    lifestyleTags: Optional[list] = []
    sleepScoreWD: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    sleepScoreWE: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    cleanlinessScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    noiseToleranceScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    guestsScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    personalityScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    smokingScore: Optional[dict] = {"value": 0.0, "isDealBreaker": False}
    sharedSpaceScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}
    communicationScore: Optional[dict] = {"value": 5.0, "isDealBreaker": False}


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


async def _get_next_id() -> int:
    last = await users_collection.find_one(sort=[("id", -1)])
    return (last["id"] + 1) if last else 1


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(request: Request, body: RegisterRequest):
    existing = await users_collection.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = await _get_next_id()
    user_doc = {
        "id": user_id,
        "email": body.email.lower(),
        "hashed_password": hash_password(body.password),
        "username": body.username,
        "matched": False,
        "matchCount": 0,
        "matchedWith": [],
        "bio": body.bio,
        "photoUrl": "",
        "lifestyleTags": body.lifestyleTags,
        "gender": body.gender,
        "sleepScoreWD": body.sleepScoreWD,
        "sleepScoreWE": body.sleepScoreWE,
        "cleanlinessScore": body.cleanlinessScore,
        "noiseToleranceScore": body.noiseToleranceScore,
        "guestsScore": body.guestsScore,
        "personalityScore": body.personalityScore,
        "smokingScore": body.smokingScore,
        "sharedSpaceScore": body.sharedSpaceScore,
        "communicationScore": body.communicationScore,
    }

    await users_collection.insert_one(user_doc)
    user_doc.pop("_id", None)
    user_doc.pop("hashed_password", None)

    token = create_access_token({"sub": str(user_id)})
    return TokenResponse(access_token=token, user=user_doc)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginRequest):
    user = await users_collection.find_one({"email": body.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    hashed = user.get("hashed_password", "")
    if not hashed or not verify_password(body.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.pop("_id", None)
    user.pop("hashed_password", None)

    token = create_access_token({"sub": str(user["id"])})
    return TokenResponse(access_token=token, user=user)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
