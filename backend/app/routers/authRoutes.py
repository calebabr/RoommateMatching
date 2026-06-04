import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from pymongo import ReturnDocument
from app.database import users_collection, counters_collection
from app.auth.utils import hash_password, verify_password, create_access_token, validate_password_strength, calculate_age
from app.auth.dependencies import get_current_user, _admin_ids
from app.limiter import limiter
from app.models import Preference, ALLOWED_LIFESTYLE_TAGS, UserInDB
from app.services.recommendationService import RecommendationService
from app.services.userProfileService import UserProfileService

_rec_service = RecommendationService()
_profile_service = UserProfileService()

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
    dateOfBirth: Optional[str] = None  # ISO date string YYYY-MM-DD
    termsVersion: Optional[str] = None  # e.g. "2026-06-03"

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
    refresh_token: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., max_length=128)


async def _generate_refresh_token(user_id: int) -> str:
    """Generate a new refresh token, store its hash on the user doc, return plain token."""
    plain = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    await users_collection.update_one(
        {"id": user_id},
        {"$set": {"refresh_token_hash": token_hash, "refresh_token_expires": expires}},
    )
    return plain


async def _get_next_id() -> int:
    result = await counters_collection.find_one_and_update(
        {"_id": "user_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["seq"]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(request: Request, body: RegisterRequest):
    existing = await users_collection.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if body.dateOfBirth is not None:
        try:
            age = calculate_age(body.dateOfBirth)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid dateOfBirth format. Use YYYY-MM-DD.")
        if age < 18:
            raise HTTPException(status_code=400, detail="You must be at least 18 years old to register.")

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
        "createdAt": datetime.now(timezone.utc),
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
    if body.dateOfBirth is not None:
        user_doc["dateOfBirth"] = body.dateOfBirth
    if body.termsVersion is not None:
        user_doc["termsVersion"] = body.termsVersion
        user_doc["termsAcceptedAt"] = datetime.utcnow().isoformat()

    await users_collection.insert_one(user_doc)
    user_doc.pop("_id", None)
    user_doc.pop("hashed_password", None)

    # Recompute recommendations for new user and all existing users
    try:
        all_users = await _profile_service.get_all_active_users()
        if len(all_users) >= 2:
            user_dicts = [UserInDB(**u).toMatchDict() for u in all_users]
            new_user_dict = UserInDB(**user_doc).toMatchDict()
            await _rec_service.on_new_user(new_user_dict, user_dicts)
    except Exception:
        pass  # never block registration if recompute fails

    token = create_access_token({"sub": str(user_id)})
    refresh_token = await _generate_refresh_token(user_id)
    return TokenResponse(access_token=token, refresh_token=refresh_token, user=user_doc)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginRequest):
    user = await users_collection.find_one({"email": body.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    hashed = user.get("hashed_password", "")
    if not hashed or not verify_password(body.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Account has been banned")

    user.pop("_id", None)
    user.pop("hashed_password", None)
    user["is_admin"] = user["id"] in _admin_ids()

    token = create_access_token({"sub": str(user["id"])})
    refresh_token = await _generate_refresh_token(user["id"])
    return TokenResponse(access_token=token, refresh_token=refresh_token, user=user)


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    current_user["is_admin"] = current_user["id"] in _admin_ids()
    return current_user


@router.post("/refresh")
@limiter.limit("10/hour")
async def refresh_token(request: Request, body: RefreshRequest):
    """Exchange a valid refresh token for a new access token and rotated refresh token."""
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    user = await users_collection.find_one({"refresh_token_hash": token_hash})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    expires = user.get("refresh_token_expires")
    if expires is None or (expires.tzinfo is None and expires.replace(tzinfo=timezone.utc) <= now) or (expires.tzinfo is not None and expires <= now):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    # Rotate: generate new refresh token
    new_refresh = await _generate_refresh_token(user["id"])
    new_access = create_access_token({"sub": str(user["id"])})
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/logout")
@limiter.limit("10/hour")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Invalidate the current user's refresh token."""
    await users_collection.update_one(
        {"id": current_user["id"]},
        {"$unset": {"refresh_token_hash": "", "refresh_token_expires": ""}},
    )
    return {"message": "Logged out"}


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=128)
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


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/hour")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    import secrets, hashlib
    from datetime import datetime, timedelta, timezone
    email_lower = body.email.lower()
    user = await users_collection.find_one({"email": email_lower})
    # Always return 200 to avoid revealing whether email exists
    if user:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await users_collection.update_one(
            {"email": email_lower},
            {"$set": {"reset_token_hash": token_hash, "reset_token_expires": expires}},
        )
        return {
            "reset_token": token,
            "message": "If that email exists, a reset token has been generated. In production this will be emailed automatically.",
        }
    return {"message": "If that email exists, a reset token has been generated."}


@router.post("/reset-password", status_code=200)
@limiter.limit("5/hour")
async def reset_password(request: Request, body: ResetPasswordRequest):
    import hashlib
    from datetime import datetime, timezone
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    user = await users_collection.find_one({
        "reset_token_hash": token_hash,
        "reset_token_expires": {"$gt": now},
    })
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"hashed_password": hash_password(body.new_password)},
            "$unset": {"reset_token_hash": "", "reset_token_expires": ""},
        },
    )
    return {"message": "Password reset successfully"}


class RestoreAccountRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=128)


@router.post("/restore-account", status_code=200)
@limiter.limit("10/hour")
async def restore_account(request: Request, body: RestoreAccountRequest):
    """Restore a soft-deleted account using the plain restore token (valid 7 days)."""
    from app.services.deletionService import DeletionService
    svc = DeletionService()
    try:
        user = await svc.restore_account(body.token)
        token = create_access_token({"sub": str(user["id"])})
        return {"message": "Account restored", "access_token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
