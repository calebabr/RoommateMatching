# Session Summary: Photo Upload Hardening

**Date:** 2026-05-29
**Agents:** Backend Agent, Tests Agent, Documentation Agent
**Task ID:** B4

---

## What Was Done

Hardened the `POST /api/users/{user_id}/upload-photo` endpoint in `backend/app/routers/userRoutes.py` to prevent MIME spoofing, EXIF data leaks, oversized uploads, and predictable filenames. Local disk storage was replaced with Cloudinary.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/routers/userRoutes.py` | Added `_detect_image_type()` (magic bytes, not Content-Type), `_reencode_image()` (Pillow, strips EXIF), Cloudinary upload replacing local disk, UUID filename, 413 for oversized, dimension validation 100×100–4000×4000, backward-compat deletion of legacy `/uploads/` files |
| `backend/requirements.txt` | Added `Pillow==10.4.0`, `cloudinary==1.40.0`, `piexif==1.1.3` |
| `backend/test_photo_upload.py` | New — 12 pytest tests, no live server or DB needed |

---

## Key Decisions

- **Magic bytes before Content-Type** — `_detect_image_type()` reads the first 12 bytes of the upload to determine file type. Content-Type header is never consulted for security decisions, preventing MIME spoofing attacks.
- **Pillow re-encode strips all EXIF unconditionally** — Rather than selectively removing sensitive tags (GPS, etc.), `_reencode_image()` re-encodes the image from scratch via Pillow. This is simpler and more robust; no EXIF survives.
- **Cloudinary `public_id` is the UUID stem** — The stored filename is a UUID (no extension). This makes filenames deterministic and traceable without leaking original upload names.
- **Old photo deletion is non-fatal** — Exceptions from deleting the previous Cloudinary asset (or legacy local file) are caught and silently ignored. An upload never fails because cleanup failed.
- **Legacy `/uploads/` local files still deleted on photo replacement** — Backward compatibility for existing users whose `photoUrl` still points to a local static path.
- **`piexif` is a test-only dependency** — Used only in `test_photo_upload.py` to construct EXIF-tagged fixture images. Production code uses Pillow only.

---

## Acceptance Criteria Met

- Oversized file (>5 MB) returns 413
- Wrong MIME (GIF bytes, PHP bytes) returns 400
- Fake-extension attack (PHP file named `.jpg`) returns 400
- EXIF GPS tag stripped — verified by intercepting bytes sent to Cloudinary and reading back with `piexif`
- Valid JPEG, PNG, and WebP uploads succeed
- Dimension bounds enforced (100×100 minimum, 4000×4000 maximum)
- Auth enforcement — unauthenticated request returns 401/403
- UUID filename — returned `photoUrl` contains a UUID, not the original filename

---

## New Environment Variables Required

| Variable | Purpose |
|----------|---------|
| `CLOUDINARY_CLOUD_NAME` | Cloudinary account cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |

---

## Open Items / Follow-Up

- Cloudinary credentials are not yet documented in any `.env.example` or deployment docs — should be added before any staging/production deploy.
- No frontend changes were made — `api.js` upload function is unchanged. Cloudinary URLs are standard HTTPS and work directly as `<img src>` values.
