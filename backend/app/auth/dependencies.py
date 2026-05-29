from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.utils import decode_token
from app.database import users_collection, matches_collection

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await users_collection.find_one({"id": int(user_id)})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user.pop("_id", None)
    user.pop("hashed_password", None)
    return user


async def get_current_user_or_403(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user


async def verify_match_exists(user_id: int, partner_id: int) -> None:
    match = await matches_collection.find_one({
        "$or": [
            {"user1_id": user_id, "user2_id": partner_id},
            {"user1_id": partner_id, "user2_id": user_id},
        ]
    })
    if match is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not matched with this user")
