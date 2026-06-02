"""
Root conftest for the backend/ test directory.

Applies to all test files at this level (test_*.py) and subdirectories.
"""
import os
import pytest

os.environ.setdefault("ROOMMATCH_ENV", "test")
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset in-memory slowapi storage before each test.

    Without this, successful register/login calls in one test file exhaust the
    per-IP rate limit budget and cause 429 failures in later tests that run in
    the same pytest session.
    """
    from app.limiter import limiter
    storage = limiter._storage
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "_storage") and isinstance(storage._storage, dict):
        storage._storage.clear()
    yield
