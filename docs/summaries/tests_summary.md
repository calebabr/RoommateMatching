# RoomMatch Test Coverage Summary

## 1. Current State

Two backend integration test scripts exist, both run against a **live server + live MongoDB**. There are no unit tests, no pytest fixtures, and no frontend tests of any kind.

## 2. Test Files

| File | Tests | Count |
|------|-------|-------|
| `backend/test_api.py` | Health check, user CRUD (create/get/update/delete), duplicate rejection, match score, dealbreaker score=0, recommendations (recompute + top-matches), like flow, mutual-like to match, self-like rejection, unmatch, bulk JSON upload | 14 |
| `backend/test_api_v2.py` | All of v1 plus: root version endpoint, all 9 preference fields validated, identical-users high score, like-while-matched rejection, unmatch-when-not-matched rejection, photo upload/delete/size-limit, chat send+retrieve, bidirectional chat, polling with `after` timestamp, conversations list, unmatched-user chat blocked, empty message rejected, self-message rejected, message persistence | 35 |
| `backend/app/test/` | Static JSON data files only: `usersTest20.json`, `usersTest250.json`, `usersTest1000.json` — used for seeding, not automated tests |

## 3. Coverage Gaps

- **Match scoring internals**: no unit tests for `matchScore.py` logic in isolation (weight calculations, boundary values, multiple simultaneous dealbreakers)
- **Notifications**: no tests for the `/notifications` endpoints or notification creation on match/like events
- **Gender-gated matching**: no test that users only see same-gender recommendations
- **MAX\_MATCHES cap**: no test enforcing the 5-match limit
- **Authentication/login**: no tests for password hashing, login endpoint, or session handling
- **Cluster/recommendation algorithm**: recompute is called but internal clustering logic is untested
- **Frontend**: zero test files; no component tests, no API service mock tests, no E2E tests

## 4. Test Infrastructure

- `pytest==7.4.4` and `pytest-asyncio==0.23.3` are in `requirements.txt` but **never used** — both test files are plain Python scripts run with `python test_api.py`
- `httpx==0.25.2` is installed (needed for FastAPI `TestClient`) but unused
- No `conftest.py`, no `pytest.ini`, no test database configuration
- No Vitest or Jest config in `frontendv2/`; `vite.config.js` has no test block

## 5. TODOs

- **Convert to pytest**: refactor scripts into proper `test_*.py` modules using `pytest` and `httpx.AsyncClient` with `pytest-asyncio`
- **Isolate test DB**: add a `conftest.py` that points Motor at a separate `roommatch_test` database and tears it down after each session
- **Unit-test matchScore.py** directly without HTTP round-trips
- **Add notification tests**: cover like-received and match-created notification creation
- **Add gender-gate and MAX\_MATCHES tests**
- **Frontend**: add Vitest + React Testing Library; at minimum test `AuthContext`, `api.js` service layer, and the like/match UI flow
