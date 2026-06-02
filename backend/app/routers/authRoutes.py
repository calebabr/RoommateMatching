from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from app.database import users_collection
from app.auth.utils import hash_password, verify_password, create_access_token, validate_password_strength
from app.auth.dependencies import get_current_user
from app.limiter import limiter
from app.models import Preference, ALLOWED_LIFESTYLE_TAGS

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)
    username: str = Field(..., min_length=1, max_length=30, pattern=r'^[A-Za-z0-9_-]+$')
    gender: Optional[str] = Field("", max_length=10)
    bio: Optional[str] = Field("", max_length=500)
    lifestyleTags: Optional[List[str]] = Field(default_factory=list, max_length=10)
    sleepScoreWD: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    sleepScoreWE: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    cleanlinessScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    noiseToleranceScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    guestsScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    personalityScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    smokingScore: Optional[Preference] = Preference(value=0.0, isDealBreaker=False)
    sharedSpaceScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)
    communicationScore: Optional[Preference] = Preference(value=5.0, isDealBreaker=False)

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, v):
        if v is None or v == "":
            return ""
        if v not in ("male", "female"):
            raise ValueError("gender must be 'male' or 'female'")
        return v

    @field_validator("bio", mode="before")
    @classmethod
    def strip_bio_html(cls, v):
        if v is None:
            return ""
        import nh3
        return nh3.clean(str(v), tags=set())

    @field_validator("lifestyleTags", mode="before")
    @classmethod
    def validate_lifestyle_tags(cls, v):
        if v is None:
            return []
        import nh3
        cleaned = []
        for tag in v:
            tag = nh3.clean(str(tag), tags=set()).strip()
            if tag not in ALLOWED_LIFESTYLE_TAGS:
                raise ValueError(f"Invalid lifestyle tag: {tag}")
            cleaned.append(tag)
        return cleaned


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


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

    try:
        validate_password_strength(body.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

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
        "sleepScoreWD": body.sleepScoreWD.model_dump(),
        "sleepScoreWE": body.sleepScoreWE.model_dump(),
        "cleanlinessScore": body.cleanlinessScore.model_dump(),
        "noiseToleranceScore": body.noiseToleranceScore.model_dump(),
        "guestsScore": body.guestsScore.model_dump(),
        "personalityScore": body.personalityScore.model_dump(),
        "smokingScore": body.smokingScore.model_dump(),
        "sharedSpaceScore": body.sharedSpaceScore.model_dump(),
        "communicationScore": body.communicationScore.model_dump(),
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


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., max_length=128)


@router.post("/change-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    user = await users_collection.find_one({"id": current_user["id"]})
    if not user or not verify_password(body.current_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await users_collection.update_one(
        {"id": current_user["id"]},
        {"$set": {"hashed_password": hash_password(body.new_password)}},
    )
    return {"message": "Password updated successfully"}
