import base64
import json
import os
from datetime import timedelta

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-for-jwt-tests")

from app.auth.utils import create_access_token, decode_token, ALGORITHM, SECRET_KEY
from jose import jwt as jose_jwt


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _build_none_alg_token(payload: dict) -> str:
    header = _b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    return f"{header}.{body}."


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_token_round_trips():
    token = create_access_token({"sub": "42", "username": "testuser"})
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["username"] == "testuser"


def test_exp_claim_present():
    token = create_access_token({"sub": "1"})
    payload = decode_token(token)
    assert payload is not None
    assert "exp" in payload


def test_custom_expiry_accepted():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=30))
    assert decode_token(token) is not None


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------

def test_already_expired_returns_none():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    assert decode_token(token) is None


def test_expired_by_24h_returns_none():
    token = create_access_token({"sub": "1"}, expires_delta=timedelta(hours=-24))
    assert decode_token(token) is None


# ---------------------------------------------------------------------------
# Algorithm enforcement
# ---------------------------------------------------------------------------

def test_hs512_signed_token_rejected():
    import time
    token = jose_jwt.encode(
        {"sub": "1", "exp": int(time.time()) + 3600},
        SECRET_KEY,
        algorithm="HS512",
    )
    assert decode_token(token) is None


def test_hs384_signed_token_rejected():
    import time
    token = jose_jwt.encode(
        {"sub": "1", "exp": int(time.time()) + 3600},
        SECRET_KEY,
        algorithm="HS384",
    )
    assert decode_token(token) is None


def test_hs256_still_accepted():
    import time
    token = jose_jwt.encode(
        {"sub": "1", "exp": int(time.time()) + 3600},
        SECRET_KEY,
        algorithm="HS256",
    )
    assert decode_token(token) is not None


# ---------------------------------------------------------------------------
# "none" algorithm
# ---------------------------------------------------------------------------

def test_none_alg_token_rejected():
    import time
    token = _build_none_alg_token({"sub": "attacker", "exp": int(time.time()) + 9999})
    assert decode_token(token) is None


def test_none_alg_with_admin_claim_rejected():
    import time
    token = _build_none_alg_token({"sub": "attacker", "role": "admin", "exp": int(time.time()) + 9999})
    assert decode_token(token) is None


# ---------------------------------------------------------------------------
# Tampered token
# ---------------------------------------------------------------------------

def test_tampered_signature_rejected():
    token = create_access_token({"sub": "1"})
    parts = token.split(".")
    sig = parts[2]
    parts[2] = sig[:-4] + ("XXXX" if not sig.endswith("XXXX") else "YYYY")
    assert decode_token(".".join(parts)) is None


def test_tampered_payload_rejected():
    token = create_access_token({"sub": "legitimate"})
    header, body, sig = token.split(".")
    padding = "=" * (-len(body) % 4)
    decoded_body = json.loads(base64.urlsafe_b64decode(body + padding))
    decoded_body["sub"] = "attacker"
    new_body = _b64url_encode(json.dumps(decoded_body).encode())
    assert decode_token(f"{header}.{new_body}.{sig}") is None


def test_garbage_token_returns_none():
    assert decode_token("this.is.garbage") is None


def test_empty_string_returns_none():
    assert decode_token("") is None
