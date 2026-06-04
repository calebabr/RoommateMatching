import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt

_secret_key_raw = os.environ.get("SECRET_KEY")
_roommatch_env = os.environ.get("ROOMMATCH_ENV", "")
if _secret_key_raw:
    SECRET_KEY = _secret_key_raw
elif _roommatch_env in ("test", "development"):
    SECRET_KEY = "dev-only-secret-not-for-production"
else:
    raise RuntimeError("SECRET_KEY environment variable must be set")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


MIN_PASSWORD_LENGTH = int(os.environ.get("MIN_PASSWORD_LENGTH", "8"))

def validate_password_strength(plain: str) -> None:
    if len(plain) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    from zxcvbn import zxcvbn
    result = zxcvbn(plain)
    if result["score"] < 2:
        feedback = result["feedback"]["suggestions"]
        hint = feedback[0] if feedback else "Choose a stronger password"
        raise ValueError(f"Password too weak: {hint}")


# Tokens expire in 24h — no refresh flow; users must re-login after expiry.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def calculate_age(dob_str: str) -> int:
    """Return the age in whole years for an ISO date string (YYYY-MM-DD)."""
    dob = date.fromisoformat(dob_str)
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_signature": True})
    except JWTError:
        return None
