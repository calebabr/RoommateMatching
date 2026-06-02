# RoomMatch Test Coverage Summary

## 1. Current State

Fifteen backend test files now exist: two legacy scripts and thirteen pytest modules. Unit tests, pytest fixtures, an isolated test database, and two `conftest.py` files exist (one root-level, one under `backend/tests/`). No frontend tests of any kind are present.

## 2. Test Files

| File | Type | Tests | Notes |
|------|------|-------|-------|
| `backend/test_api.py` | Legacy script (python, not pytest) | 14 | Health, user CRUD, match score, dealbreaker, recommendations, like/match/unmatch, bulk upload |
| `backend/test_api_v2.py` | Legacy script (python, not pytest) | 35 | All of v1 plus photo upload/delete, chat, bidirectional chat, after-timestamp polling, unmatched chat blocked |
| `backend/test_password_security.py` | pytest | 17 | 10 unit + 7 API; bcrypt rounds=12, verify, zxcvbn rejections (including "password123"), env override, register/login/change-password flows; mocks MongoDB, no live DB needed |
| `backend/test_ratelimits.py` | pytest async | 6 | Tests login/register/like/chat/upload/default rate limits; stub app, no live DB |
| `backend/test_idor.py` | pytest async | 20 | Tests `get_current_user_or_403` and `verify_match_exists` in isolation; stub app, no live DB |
| `backend/test_idor_integration.py` | pytest async | 15 | IDOR tests against real app + live MongoDB; checks 403 responses do not leak user data |
| `backend/tests/test_auth.py` | pytest | 24 | Register (8), Login (7), /me (7), full round-trip (2); uses `conftest.py` test DB |
| `backend/tests/test_jwt.py` | pytest unit | 14 | JWT encode/decode, expiry, algorithm enforcement, "none" algorithm rejected, tampered tokens |
| `backend/tests/test_password.py` | pytest | 17 | Hash rounds, salt randomness, weak/strong password validation, endpoint tests via AsyncClient |
| `backend/test_validation.py` | pytest | 41 | Username/bio/gender/lifestyle/preference/body-size/HTML-sanitization/error-format negative tests; stub app, no live DB |
| `backend/test_atomic_id.py` | pytest async | 2 | Concurrent (10 simultaneous registrations → 10 unique IDs) and sequential ID generation; validates `$inc`-based counter approach |
| `backend/test_admin_gate.py` | pytest async | 4 | Non-admin 403 on recompute and uploadUsers; admin 200 on both; validates `get_admin_user` dependency |
| `backend/test_password_reset.py` | pytest async | 7 | Valid reset flow, unknown-email no info leak, invalid token 400, expired token 400, reused token 400, weak password 400; tests both forgot-password and reset-password endpoints |
| `backend/test_likes_sent.py` | pytest async | 3 | `getLikesSent` contains target after like, empty for user who sent no likes, unauthenticated returns 401/403; AsyncMock collections (same pattern as test_admin_gate.py) |
| `backend/test_migrate_indexes.py` | pytest | 2 | `create_indexes()` against `roommatch_migrate_test` DB creates all expected indexes with correct uniqueness; idempotent second run raises no error |
| `backend/test_ban.py` | pytest async | 7 | Admin ban/unban endpoints and login ban check; AsyncMock collections, no live DB needed |
| `backend/app/test/` | JSON data only | — | `usersTest20.json`, `usersTest250.json`, `usersTest1000.json` — seed data, not automated tests |

## 3. Test Infrastructure

- `backend/pytest.ini` — exists; sets `asyncio_mode = auto`, session-scoped loops
- `backend/tests/conftest.py` — exists; session-scoped fixture drops/recreates `roommatch_test` DB; per-test autouse fixture patches all three import sites (`app.database`, `app.routers.authRoutes`, `app.auth.dependencies`) with an `AsyncMongoWrapper` backed by the test DB
- `backend/conftest.py` (root-level, new 2026-05-29) — provides an `autouse` `reset_rate_limiter` fixture that clears slowapi's in-memory storage before each test; prevents rate-limit state from bleeding across test files in the same pytest session
- `pytest`, `pytest-asyncio`, and `httpx` — all now actively used (not just installed)
- `slowapi==0.1.9`, `zxcvbn==4.4.28`, and `nh3==0.2.17` added to `requirements.txt`

## 4. Coverage Gaps

- **Match scoring internals**: no unit tests for `matchScore.py` logic in isolation (weight calculations, boundary values, multiple simultaneous dealbreakers)
- **Notification creation**: IDOR tests check 403/200 on GET, but no tests for notification creation triggered by like/match events
- **Gender-gated matching**: no test that users only see same-gender recommendations
- **MAX\_MATCHES cap**: no test enforcing the 5-match limit
- **Cluster/recommendation algorithm**: recompute is called but internal clustering logic is untested
- **Token invalidation on logout**: no logout endpoint exists, so this is untested
- **Frontend**: zero test files; no Vitest, no React Testing Library, no component tests, no E2E tests
- **Legacy scripts not converted**: `test_api.py` and `test_api_v2.py` are still plain Python scripts, not pytest modules

## 5. TODOs

**Completed**
- Isolate test DB — done via `backend/tests/conftest.py`
- Authentication tests — login endpoint, password hashing, change-password, and JWT security all covered
- Convert to pytest — substantially done for all new files; legacy scripts remain
- Validation hardening tests — `test_validation.py` (41 tests) covers all new Pydantic constraints: username pattern, bio length, gender literal, lifestyle tag whitelist, preference bounds, 1 MB body-size middleware, HTML sanitization, and clean 422 error format (2026-05-29)
- Root-level `conftest.py` — `reset_rate_limiter` autouse fixture prevents rate-limit bleed across test files in a single session (2026-05-29)
- Atomic ID tests — `test_atomic_id.py` (2 tests) validates concurrent and sequential ID generation via `$inc` counter (2026-06-02)
- Admin gate tests — `test_admin_gate.py` (4 tests) validates `get_admin_user` 403/200 on recompute and uploadUsers (2026-06-02)
- Password reset tests — `test_password_reset.py` (7 tests) covers valid flow, enumeration resistance, and all invalid-token cases (2026-06-02)
- Like-sent / like button state tests — `test_likes_sent.py` (3 tests) covers `getLikesSent` API correctness and auth enforcement (2026-06-02)
- Index migration tests — `test_migrate_indexes.py` (2 tests) confirms `create_indexes()` creates correct indexes and is idempotent (2026-06-02)
- Ban/unban admin endpoint tests — `test_ban.py` (7 tests) covers admin ban/unban 200, non-admin 403, 404 for missing user, banned user login 403, and unbanned user login 200 (2026-06-02)

**Still TODO**
- Unit-test `matchScore.py` directly without HTTP round-trips
- Add notification creation tests (like-received, match-created events)
- Add gender-gate and MAX\_MATCHES tests
- Convert `test_api.py` and `test_api_v2.py` to proper pytest modules
- Frontend: add Vitest + React Testing Library; at minimum test `AuthContext`, `api.js` service layer, and the like/match UI flow
