"""
Tests for the hardened photo upload endpoint.

POST /api/users/{user_id}/upload-photo

Spec:
  - Rate limited 10/hour
  - Requires Bearer token, get_current_user_or_403 dependency
  - Rejects files > 5MB with HTTP 413
  - Validates magic bytes (not Content-Type):
      JPEG:  FF D8 FF
      PNG:   89 50 4E 47 0D 0A 1A 0A
      WebP:  bytes 0-3 == 52 49 46 46 AND bytes 8-11 == 57 45 42 50
      Other: HTTP 400
  - Opens with Pillow, checks dimensions: <100x100 → 400, >4000x4000 → 400
  - Re-encodes with Pillow (strips EXIF)
  - Stores on Cloudinary, saves secure_url to user's photoUrl field
  - Returns {"photoUrl": "<cloudinary_url>", "filename": "<uuid>.<ext>"}

All external calls (Cloudinary, MongoDB) are mocked — no live server required.

Run with:
    cd backend
    pytest test_photo_upload.py -v
"""

import os
import io
import re
import uuid

# Must be set before importing anything from the app so auth/utils picks up
# the dev secret key instead of raising RuntimeError.
os.environ.setdefault("ROOMMATCH_ENV", "test")

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from httpx import AsyncClient, ASGITransport
from PIL import Image

# ---------------------------------------------------------------------------
# Try to import piexif; fall back gracefully if it is not installed.
# ---------------------------------------------------------------------------
try:
    import piexif
    _PIEXIF_AVAILABLE = True
except ImportError:
    _PIEXIF_AVAILABLE = False

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def make_jpeg(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def make_png(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_webp(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


def make_jpeg_with_exif(width: int = 200, height: int = 200) -> bytes:
    """Return a JPEG with GPS EXIF data (tag 34853) embedded via piexif."""
    import piexif
    exif_dict = {"GPS": {piexif.GPSIFD.GPSLatitude: ((35, 1), (0, 1), (0, 1))}}
    exif_bytes = piexif.dump(exif_dict)
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fake user returned by the mocked userProfileService.get_user
# ---------------------------------------------------------------------------
FAKE_USER = {
    "id": 1,
    "username": "testuser",
    "email": "test@auburn.edu",
    "photoUrl": "",
    "gender": "male",
    "matched": False,
    "matchCount": 0,
    "matchedWith": [],
}

CLOUDINARY_FAKE_URL = "https://res.cloudinary.com/test/image/upload/test.jpg"

# ---------------------------------------------------------------------------
# Module-level token (generated once, reused across all tests)
# ---------------------------------------------------------------------------

def _make_token(user_id: int = 1) -> str:
    from app.auth.utils import create_access_token
    return create_access_token({"sub": str(user_id)})


TOKEN_USER1 = _make_token(1)
TOKEN_USER2 = _make_token(2)

HEADERS_USER1 = {"Authorization": f"Bearer {TOKEN_USER1}"}
HEADERS_USER2 = {"Authorization": f"Bearer {TOKEN_USER2}"}

# ---------------------------------------------------------------------------
# App fixture — creates a fresh TestClient with all external deps mocked
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client():
    """
    Yield an async HTTP client pointing at the real FastAPI app, but with:
      - Cloudinary upload/destroy patched to no-ops
      - userProfileService.get_user returning FAKE_USER
      - userProfileService.collection.update_one mocked (AsyncMock)
      - app.auth.dependencies.users_collection.find_one returning FAKE_USER
        so that the Bearer-token auth middleware can resolve the user without
        hitting a real MongoDB instance
    """
    from app.main import app

    # Build a mock users_collection whose find_one returns FAKE_USER for id=1
    # and None for any other id (simulates "user not found → 401").
    mock_users_coll = MagicMock()

    async def _find_one(filter=None, **kwargs):
        uid = None
        if filter and "id" in filter:
            uid = filter["id"]
        if uid == 1:
            return dict(FAKE_USER)
        return None

    mock_users_coll.find_one = _find_one

    # Mock collection.update_one used inside upload_photo to persist photoUrl
    mock_update_one = AsyncMock(return_value=MagicMock(matched_count=1))

    with (
        patch("app.auth.dependencies.users_collection", mock_users_coll),
        patch(
            "app.routers.userRoutes.cloudinary.uploader.upload",
            return_value={"secure_url": CLOUDINARY_FAKE_URL},
        ),
        patch("app.routers.userRoutes.cloudinary.uploader.destroy"),
        patch(
            "app.routers.userRoutes.userProfileService.get_user",
            new=AsyncMock(return_value=dict(FAKE_USER)),
        ),
        patch(
            "app.routers.userRoutes.userProfileService.collection.update_one",
            new=mock_update_one,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as ac:
            yield ac


# ===========================================================================
# Acceptance tests (spec-required)
# ===========================================================================

@pytest.mark.asyncio
async def test_oversized_file_rejected(client):
    """6 MB payload of valid JPEG magic bytes must be rejected with 413."""
    # Prepend valid JPEG magic then pad to 6 MB
    magic = bytes([0xFF, 0xD8, 0xFF, 0xE0])
    payload = magic + b"\x00" * (6 * 1024 * 1024 - len(magic))

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("big.jpg", payload, "image/jpeg")},
    )
    assert resp.status_code == 413, (
        f"Expected 413 for oversized file, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_wrong_mime_rejected(client):
    """GIF magic bytes must be rejected with 400 (not in allowed set)."""
    gif_magic = bytes([0x47, 0x49, 0x46, 0x38])  # GIF8
    payload = gif_magic + b"\x00" * 100

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("anim.gif", payload, "image/gif")},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for GIF magic bytes, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_fake_extension_attack_rejected(client):
    """
    A file named 'evil.jpg' whose content starts with PHP source bytes
    must be rejected with 400 — the magic-byte check fires regardless of
    the filename extension or Content-Type header.
    """
    php_payload = b"<?php system($_GET['cmd']); ?>"

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("evil.jpg", php_payload, "image/jpeg")},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for PHP content in .jpg file, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_exif_stripped_from_uploaded_image(client):
    """
    JPEG with GPS EXIF data uploaded → the bytes forwarded to Cloudinary
    must have the GPS EXIF tag removed (or _getexif() returns None / no GPS).
    """
    jpeg_with_exif = make_jpeg_with_exif()

    captured_calls: list = []

    def _capture_upload(data, **kwargs):
        captured_calls.append(data)
        return {"secure_url": CLOUDINARY_FAKE_URL}

    with patch(
        "app.routers.userRoutes.cloudinary.uploader.upload",
        side_effect=_capture_upload,
    ):
        resp = await client.post(
            "/api/users/1/upload-photo",
            headers=HEADERS_USER1,
            files={"file": ("photo.jpg", jpeg_with_exif, "image/jpeg")},
        )

    assert resp.status_code == 200, (
        f"Expected 200 for valid JPEG with EXIF, got {resp.status_code}: {resp.text}"
    )
    assert len(captured_calls) == 1, "Cloudinary upload should have been called once"

    uploaded_data = captured_calls[0]
    # uploaded_data may be bytes or a file-like object
    if hasattr(uploaded_data, "read"):
        uploaded_bytes = uploaded_data.read()
    else:
        uploaded_bytes = uploaded_data

    # Open re-encoded bytes with Pillow and verify GPS tag is absent
    uploaded_img = Image.open(io.BytesIO(uploaded_bytes))

    # Verify GPS EXIF tag (34853) is absent using Pillow's built-in getexif()
    exif = uploaded_img.getexif()
    assert 34853 not in exif, (
        "GPS EXIF tag (34853) should have been stripped by Pillow re-encoding"
    )


# ===========================================================================
# Additional robustness tests
# ===========================================================================

@pytest.mark.asyncio
async def test_valid_jpeg_accepted(client):
    """A properly formed 200×200 JPEG must be accepted (200) with photoUrl."""
    jpeg_bytes = make_jpeg(200, 200)

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid JPEG, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "photoUrl" in body, "Response must include photoUrl"
    assert body["photoUrl"] == CLOUDINARY_FAKE_URL


@pytest.mark.asyncio
async def test_valid_png_accepted(client):
    """A properly formed 200×200 PNG must be accepted (200) with photoUrl."""
    png_bytes = make_png(200, 200)

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("photo.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid PNG, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "photoUrl" in body


@pytest.mark.asyncio
async def test_valid_webp_accepted(client):
    """A properly formed 200×200 WebP must be accepted (200) with photoUrl."""
    webp_bytes = make_webp(200, 200)

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("photo.webp", webp_bytes, "image/webp")},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid WebP, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "photoUrl" in body


@pytest.mark.asyncio
async def test_image_too_small_rejected(client):
    """A 50×50 image is below the 100×100 minimum → must return 400."""
    small_jpeg = make_jpeg(50, 50)

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": ("tiny.jpg", small_jpeg, "image/jpeg")},
    )
    assert resp.status_code == 400, (
        f"Expected 400 for image too small (50x50), got {resp.status_code}: {resp.text}"
    )
    # Detail message should hint at the size constraint
    detail = resp.json().get("detail", "").lower()
    assert "small" in detail or "dimension" in detail or "size" in detail or "100" in detail, (
        f"Expected size-related error detail, got: {detail}"
    )


@pytest.mark.asyncio
async def test_image_too_large_rejected(client):
    """
    An image whose dimensions exceed 4000×4000 must be rejected with 400.

    Allocating a full 4001×4001 pixel buffer would be expensive; instead we
    patch PIL.Image.open so it returns a mock whose .size attribute reports
    (4001, 4001).  The magic-byte check runs before PIL.Image.open so we still
    supply valid JPEG bytes, but we short-circuit the actual decode.
    """
    jpeg_bytes = make_jpeg(200, 200)  # valid magic bytes + small payload

    mock_img = MagicMock()
    mock_img.size = (4001, 4001)
    mock_img.__enter__ = lambda s: s
    mock_img.__exit__ = MagicMock(return_value=False)

    with patch("app.routers.userRoutes.Image.open", return_value=mock_img):
        resp = await client.post(
            "/api/users/1/upload-photo",
            headers=HEADERS_USER1,
            files={"file": ("huge.jpg", jpeg_bytes, "image/jpeg")},
        )

    assert resp.status_code == 400, (
        f"Expected 400 for image too large (4001x4001), got {resp.status_code}: {resp.text}"
    )
    detail = resp.json().get("detail", "").lower()
    assert (
        "large" in detail
        or "dimension" in detail
        or "size" in detail
        or "4000" in detail
    ), f"Expected size-related error detail, got: {detail}"


@pytest.mark.asyncio
async def test_unauthenticated_upload_rejected(client):
    """No Authorization header → must return 401 or 403."""
    jpeg_bytes = make_jpeg()

    resp = await client.post(
        "/api/users/1/upload-photo",
        # no HEADERS_USER1
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code in (401, 403), (
        f"Expected 401 or 403 without auth, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_wrong_user_upload_rejected(client):
    """
    A user authenticated as user 1 trying to upload to user 2's profile must
    receive 403 (the get_current_user_or_403 IDOR guard).
    """
    jpeg_bytes = make_jpeg()

    resp = await client.post(
        "/api/users/2/upload-photo",
        headers=HEADERS_USER1,  # token says sub=1, but path says user_id=2
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 403, (
        f"Expected 403 for wrong-user upload, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_uuid_filename_used(client):
    """
    After a successful upload the response 'filename' field must:
      1. Match a UUID-based pattern.
      2. NOT contain any part of the original uploaded filename.
    """
    jpeg_bytes = make_jpeg()
    original_name = "my_secret_vacation_photo_2024.jpg"

    resp = await client.post(
        "/api/users/1/upload-photo",
        headers=HEADERS_USER1,
        files={"file": (original_name, jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for valid JPEG, got {resp.status_code}: {resp.text}"
    )

    body = resp.json()
    assert "filename" in body, "Response must include filename"
    filename: str = body["filename"]

    # Must match a UUID (hex or standard) pattern followed by an extension
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}"
        r"|[0-9a-f]{32}",
        re.IGNORECASE,
    )
    base = filename.rsplit(".", 1)[0]
    # Strip any leading prefix like "user_1_" to get to the UUID portion
    uuid_part = re.sub(r"^(user_\d+_)?", "", base)
    assert uuid_pattern.match(uuid_part), (
        f"Filename '{filename}' does not contain a UUID-like identifier"
    )

    # Must not leak the original filename
    original_stem = "my_secret_vacation_photo_2024"
    assert original_stem not in filename, (
        f"Filename '{filename}' must not contain the original uploaded filename"
    )
