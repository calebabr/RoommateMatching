# Session Summary: Secrets Audit (Task B1)

**Date:** 2026-05-29
**Project:** RoomMatch
**Focus:** Secrets and credential hygiene across backend, frontend, and git history

---

## Overview

A full secrets audit was run against the codebase and git history. No live credentials were found committed, but several medium/high severity issues were identified and remediated: a default JWT secret with 14-commit history, a hardcoded MongoDB URL, a committed build artifact containing an internal IP, and a missing root `.gitignore`.

---

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| FINDING-H1 | High | Default JWT `SECRET_KEY` (`"roommatch-dev-secret-change-in-prod"`) present in 14 historical commits (initial commit through `43b681fd`). | Remediated in `530dcf5b`. Key rotation required before production. |
| FINDING-M1 | Medium | Internal IP `172.17.202.174` baked into committed `frontendv2/dist/` build artifact. | `dist/` removed from git index; added to `.gitignore`. |
| FINDING-M2 | Medium | `MONGO_URL` and `MONGO_DB_NAME` hardcoded in `database.py` and `migrate_add_auth_fields.py`. | Moved to `os.environ.get(...)` with safe defaults. |
| FINDING-I1 | Info | No root `.gitignore` existed. | Created. |
| FINDING-I2 | Info | `frontendv2/dist/` was tracked in git. | Untracked via `git rm --cached`. |

**Items confirmed clean:** Cloudinary keys never hardcoded, no MongoDB Atlas URIs in history, no `.env` files ever committed, no API secrets in frontend bundle source.

---

## Files Changed / Created

| File | Change |
|---|---|
| `backend/app/database.py` | `MONGO_URL` and `MONGO_DB_NAME` moved to env vars |
| `backend/migrate_add_auth_fields.py` | Same env var change |
| `.gitignore` (root, new) | Covers `.env*`, `frontendv2/dist/`, `__pycache__/`, `node_modules/`, `backend/uploads/` |
| `backend/.env.example` (new) | Documents all backend env vars |
| `frontendv2/.env.example` (new) | Documents `VITE_API_BASE_URL` |
| `frontendv2/dist/` | Removed from git tracking |
| `backend/SECURITY_SECRETS_AUDIT.md` (new) | Full audit report |
| `docs/TASKS.md` | Task B1 row added to Completed |

---

## Open Items / Next Steps

- **JWT key rotation (mandatory):** The old default secret is in git history. Before any production deployment, generate a new `SECRET_KEY` and set it as an environment variable. All existing JWT tokens will be invalidated.
- **CORS hardening:** `allow_origins=["*"]` is still set in `main.py`. Must be restricted to the actual frontend domain before going live.
- **MongoDB access control:** `MONGO_URL` default still points to unauthenticated localhost. Production should use an authenticated URI set via env var.
- **Cloudinary keys:** Confirmed never committed, but should be rotated as a precaution if they were ever stored anywhere outside `.env` files.

---

## Agents Involved

| Agent | Responsibility |
|---|---|
| Security Agent | Full audit, remediation of M2/I1/I2, `.env.example` creation, audit report |
| Documentation Agent | `backend_summary.md` update, this session summary |
