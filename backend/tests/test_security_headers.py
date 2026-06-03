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
    csp = response.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "img-src 'self' data: https://res.cloudinary.com" in csp
    assert "connect-src 'self' https://roommatematching.onrender.com" in csp

    # P3A.6 — unsafe-inline must be absent from both script-src and style-src
    csp_directives = {
        part.strip().split()[0]: part.strip()
        for part in csp.split(";")
        if part.strip()
    }

    script_src = csp_directives.get("script-src", "")
    assert "script-src" in csp, "script-src directive missing from CSP"
    assert "'unsafe-inline'" not in script_src, (
        f"'unsafe-inline' must not appear in script-src; got: {script_src!r}"
    )

    style_src = csp_directives.get("style-src", "")
    assert "style-src" in csp, "style-src directive missing from CSP"
    assert "'unsafe-inline'" not in style_src, (
        f"'unsafe-inline' must not appear in style-src; got: {style_src!r}"
    )
    permissions = response.headers.get("permissions-policy", "")
    assert "camera=()" in permissions
    assert "microphone=()" in permissions
    assert "geolocation=()" in permissions
