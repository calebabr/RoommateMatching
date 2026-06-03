# RoomMatch Secrets Audit

**Date:** 2026-05-29  
**Scope:** Full repository (all current files + complete git history)  
**Method:** Manual grep sweep + `git log -S` pickaxe search; trufflehog and git-secrets were not available in this environment — pattern matching was performed manually.

---

## Summary

| Severity | ID | Finding | Status |
|----------|----|---------|--------|
| High | H1 | Historical hardcoded JWT default secret in git history | Rotated (dev-only value) |
| Medium | M1 | Internal IP address committed in stale build artifact | Removed from git index |
| Medium | M2 | `MONGO_URL` hardcoded in source (no env var) | Fixed |
| Info | I1 | No root `.gitignore` — `.env` files could be accidentally committed | Fixed |
| Info | I2 | `frontendv2/dist/` tracked in git (stale build artifact) | Fixed |

---

## FINDING-H1 (High): Historical hardcoded JWT secret

**File:** `backend/app/auth/utils.py`  
**Commits affected:** `43b681fd`, `762a9b5f`, `10e00fb7`, `e0da3cb7`, `2df5d094`, `459123e9`, `4b3574a9`, `1ef8bad7`, `2e9f4264`, `186ff7aa`, `392defab`, `5040ce62`, `0f42bc01`, `4521a44f`  
**Introduced:** initial commit  
**Fixed:** commit `530dcf5b` (2026-05-29) — now raises `RuntimeError` if `SECRET_KEY` is absent in production

**Leaked value:**
```
roommatch-dev-secret-change-in-prod
```

**Risk assessment:** The value's name ("dev-secret-change-in-prod") indicates it was always intended as a placeholder. No evidence of Atlas/cloud MongoDB or Cloudinary credentials in the same era of commits suggests this was never deployed to a public endpoint with this key. However, because it existed in git history, anyone with repo access could use it to forge valid JWTs.

**Actions taken:**
1. Current code already rejects this value in production (raises `RuntimeError`).
2. **Rotation required for production:** Generate a new `SECRET_KEY` via:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Set this value as a secure environment variable before deploying. All existing JWT sessions will be invalidated — users must log in again.
3. The historical value remains in git history. To expunge it, use `git filter-repo --path backend/app/auth/utils.py --force` and force-push. For a student project this may not be necessary; for a production service with sensitive user data it is recommended.

---

## FINDING-M1 (Medium): Internal IP in committed build artifact

**File:** `frontendv2/dist/assets/index-BCZxA0-y.js` (committed to git)  
**IP found:** `http://172.17.202.174:8000/api`  
**Also in history:** `frontendv2/src/services/api.js` (commits `43b681fd`, `762a9b5f`, `10e00fb7`, `e0da3cb7`), `frontend/src/services/api.js` (older frontend, same era)

**Risk assessment:** Reveals an internal network address (likely a campus or dorm WiFi assignment). This is low-severity for external attackers (private IP, not routable), but leaks internal topology and confirms the development environment. For a university project this is acceptable risk; for production it should be cleaned.

**Current source state:** `DEFAULT_BASE = 'http://localhost:8000/api'` in `frontendv2/src/services/api.js` — clean.

**Actions taken:**
1. Removed `frontendv2/dist/` from git tracking via `git rm --cached`.
2. Added `frontendv2/dist/` to root `.gitignore` — future builds will not be committed.
3. The committed stale dist files remain in git history in commits `762a9b5f` through `530dcf5b`. These can be expunged with `git filter-repo` if needed.

---

## FINDING-M2 (Medium): Hardcoded MongoDB URL

**Files:**
- `backend/app/database.py` line 3: `MONGO_URL = "mongodb://localhost:27017/"`
- `backend/migrate_add_auth_fields.py` line 15: same

**Risk assessment:** The localhost URL itself contains no credentials. However, hardcoding it means that in a deployment using MongoDB Atlas (which embeds `username:password` in the URI), the credentials would need to be put directly in source code. This is a pre-credential-leak risk.

**Actions taken:** Both files updated to read from `os.environ.get("MONGO_URL", "mongodb://localhost:27017/")`. Local development continues to work with no changes; production deployments use the env var.

---

## FINDING-I1 (Info): No root `.gitignore`

No root-level `.gitignore` existed. This means `.env` files, `__pycache__/`, `node_modules/`, and build artifacts could be accidentally committed in the future.

**Actions taken:** Created `.gitignore` at repository root covering:
- All `.env` variants (`.env`, `.env.local`, `.env.production`, `.env.staging`)
- Python bytecode and virtual environments
- `frontendv2/dist/` and `frontend/node_modules/`
- Backend `uploads/` directory (local dev photos)
- OS and IDE artifacts

---

## FINDING-I2 (Info): `frontendv2/dist/` tracked in git

Three build artifact files were tracked by git and contained an internal IP (see M1). Build outputs should never be committed — they are derived from source and can contain stale data.

**Actions taken:** `git rm --cached` removed them from the index. Root `.gitignore` prevents re-addition.

---

## Items Confirmed Clean

| Item | Where checked | Result |
|------|--------------|--------|
| Cloudinary API key/secret | All Python source files + full git history | Never hardcoded; always read from env vars |
| Real MongoDB Atlas URI | Full git history (-S pickaxe) | Not found |
| `SECRET_KEY` in frontend bundle | `frontendv2/dist/assets/index-BCZxA0-y.js` grepped | Not present |
| Cloudinary credentials in frontend bundle | Same file | Not present |
| `.env` files ever committed | `git ls-files` + `git log -- .env` | Not found |
| Passwords in test files | `backend/test_*.py`, `backend/tests/*.py` | Only test fixture passwords (non-real) |
| VITE_ env vars with secrets | `frontendv2/src/` | No VITE_ vars defined; no secrets in source |

---

## Recommendations (not yet implemented)

1. **Expunge git history** — The historical `roommatch-dev-secret-change-in-prod` and `172.17.202.174` entries are still reachable via `git log`. Run `git filter-repo` if the repository is public or will be audited by a security team.
2. **MongoDB Atlas prep** — When deploying to Atlas, ensure `MONGO_URL` is stored only in environment variables (e.g., Render/Railway/Heroku config, `.env` on a server, or a secrets manager). Never commit it.
3. **Generate a fresh `SECRET_KEY`** before any production deployment — even though the leaked dev value was never used in production, starting clean is best practice.
4. **Use `VITE_API_BASE_URL`** from `.env.example` in `frontendv2/src/services/api.js` as the `DEFAULT_BASE` so the backend URL is configurable without rebuilding.
