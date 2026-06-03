import os
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("ROOMMATCH_ENV", "test")

import pytest
from fastapi import HTTPException
from app.main import _before_send


def _make_event():
    return {
        "request": {
            "headers": {"authorization": "Bearer secret-token"},
            "cookies": {"session": "abc"},
        }
    }


def _hint(exc):
    try:
        raise exc
    except Exception:
        import sys
        return {"exc_info": sys.exc_info()}


def test_filter_401():
    assert _before_send(_make_event(), _hint(HTTPException(status_code=401))) is None


def test_filter_403():
    assert _before_send(_make_event(), _hint(HTTPException(status_code=403))) is None


def test_filter_404():
    assert _before_send(_make_event(), _hint(HTTPException(status_code=404))) is None


def test_filter_429():
    assert _before_send(_make_event(), _hint(HTTPException(status_code=429))) is None


def test_pass_500():
    result = _before_send(_make_event(), _hint(RuntimeError("boom")))
    assert result is not None


def test_strip_auth_header():
    event = _make_event()
    result = _before_send(event, _hint(RuntimeError("boom")))
    assert result["request"]["headers"]["authorization"] == "[Filtered]"


def test_strip_cookies():
    event = _make_event()
    result = _before_send(event, _hint(RuntimeError("boom")))
    assert "cookies" not in result["request"]
