import os
os.environ.setdefault("SECRET_KEY", "dev-only-secret-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_security_headers_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers.get("content-security-policy", "")
    assert "camera=()" in response.headers.get("permissions-policy", "")
