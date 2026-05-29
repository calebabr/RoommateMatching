import os
from slowapi import Limiter
from slowapi.util import get_remote_address


def _build_storage_uri() -> str:
    url = os.getenv("UPSTASH_REDIS_REST_URL", "")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    if url and token:
        # slowapi/limits uses redis:// URIs; Upstash REST is HTTP-based,
        # so fall back to in-memory if only REST credentials are present.
        redis_url = os.getenv("UPSTASH_REDIS_URL", "")
        if redis_url:
            return redis_url
    return "memory://"


def _get_user_or_ip(request) -> str:
    # Key by first 32 chars of Bearer token (unique per user) or fall back to IP
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and len(auth) > 14:
        return auth[7:39]
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip, storage_uri=_build_storage_uri())
