# RoomMatch Documentation Audit

**Date:** 2026-05-28

---

## 1. Current State

Two documentation files exist at the project root:

- **README.md** — Comprehensive and well-structured. Covers features, tech stack, prerequisites, installation, environment variables, a full API reference table, database schema, project structure tree, test instructions, and security notes. High quality.
- **CLAUDE.md** — Developer-facing project brief for the AI coding assistant. Concise and accurate for most fields, but contains one outdated note (see Notes below).

No `docs/` directory existed prior to this audit. No backend docstrings exist in `main.py`, `models.py`, or router files. The `matchScore.py` service has a single docstring on `genderCompatible`. Frontend source files (`api.js`, page components) have inline comments but no formal documentation.

`frontendAdmin/README.md` is the default Vite scaffold template — not project-specific.

---

## 2. What's Documented

- App overview and feature list
- Tech stack table
- Installation and setup steps (backend and frontend)
- Environment variables
- All API endpoints (auth, users, chat, notifications, admin)
- MongoDB collections and their purpose
- Project directory structure
- How to run tests
- Security considerations

---

## 3. Gaps

- No architecture diagram (data flow, service interaction)
- No contributor or onboarding guide
- No documentation of the match-scoring algorithm logic or weighting formula
- No frontend component reference or page-level docs
- No deployment guide (production environment, hosting, reverse proxy)
- No explanation of the recommendation/clustering pipeline
- `frontendAdmin` is completely undocumented as a project component

---

## 4. Recommended Priority

1. **Match Scoring Algorithm Doc** — The weighted preference formula and deal-breaker logic in `matchScore.py` are central to the product but entirely undocumented for contributors.
2. **Architecture / Data Flow Diagram** — A diagram showing frontend -> API -> MongoDB -> recommendation engine would significantly reduce onboarding time.
3. **Deployment Guide** — `README.md` covers local dev only; a production setup guide (env hardening, MongoDB auth, reverse proxy, CORS lockdown) is needed before any real launch.

---

## 5. Notes

- **Inconsistency:** `CLAUDE.md` states auth uses "localStorage-based sessions (no JWT/OAuth yet)", but `README.md` and the actual codebase both implement JWT via `python-jose`. `CLAUDE.md` is outdated on this point and should be updated to reflect the current JWT auth implementation.
- The `frontendAdmin` directory contains a separate React/Vite app with only a scaffold README — its purpose and relationship to the main app are undocumented.
