# RoomMatch

A roommate matching web application for college students. Users create profiles with lifestyle preferences, receive compatibility-scored recommendations, like and match with each other, and chat in real time.

For task tracking see [docs/TASKS.md](docs/TASKS.md).

---

## Features

- **Profile creation** — name, gender, bio, photo (Cloudinary), lifestyle preferences (sleep schedule, cleanliness, noise tolerance, guests, personality, smoking, shared space, communication), lifestyle tags, religion tag, major, graduation year/season
- **Profile prompts** — up to 3 answers from a curated 20-prompt catalogue served by the API (never hardcoded client-side); rendered as cards on profiles and discover
- **Discover filters** — filter the feed by major, graduation year, lifestyle tags, religion, housing type, budget, and minimum score; persisted per user in localStorage, never in the URL
- **Soft profile prompts** — users missing major or graduation year are gently prompted to fill them in
- **Housing intent** — housing type (on-campus / off-campus / either), preferred location, monthly budget range, lease term, and move-in season/year; incompatible housing type or non-overlapping budgets are hard filters on recommendations, and a move-in mismatch multiplies the score by 0.7
- **Matching algorithm** — weighted preference comparison with deal-breaker logic in `matchScore.py`; gender-gated (same-gender only); max 5 matches per user
- **Compatibility score breakdown** — collapsible "Why this score" panel on a profile, showing per-category scores, deal-breaker flags, and a bucketed difference (`same` / `close` / `different`) rather than the other user's raw preference values
- **Likes / Matches** — like others, cancel pending likes, mutual like creates a match; unmatching supported
- **Roommate groups** — form a 2–4 person same-gender group with your matches; invite (14-day expiry), accept/decline, leave or disband; pairwise compatibility matrix with group average and weakest pair; group membership does not consume the 5-match cap
- **"Found a roommate" status** — distinct from pausing: hides you from discover, likes, and recommendations while keeping existing matches and chats reachable; undoable
- **Skip / Pass** — pass on a discover profile; skipped users hidden for 30 days (`swipes` collection with TTL index)
- **Chat** — per-match conversation threads; iMessage-style read receipts ("Seen [time]"), unread badge on nav icon, "New messages" divider, relative timestamps
- **Notifications** — in-app notifications for new likes, matches, and messages
- **Age verification** — date of birth required at signup; under-18 accounts blocked
- **Terms of Service / Privacy Policy** — in-app modal on first login; versioned (`CURRENT_TERMS_VERSION` in `App.jsx`); in-app pages at `/terms` and `/privacy`
- **Account management** — pause profile (hidden from discover), deactivate account, soft-delete with 7-day restore window, GDPR data export, account restoration
- **Block & Report** — block/unblock users (auto-unmatch); report with reason; auto-block on report
- **Token refresh** — silent 30-day refresh token rotation; server-side logout invalidation
- **Rate limiting** — slowapi; public endpoints limited by IP, authenticated endpoints by user ID; Upstash Redis in production, in-memory fallback locally
- **Security** — bcrypt passwords, JWT (HS256, 24h access / 30d refresh), CORS locked to `FRONTEND_URL`, security headers (HSTS, CSP with no `unsafe-inline`, X-Frame-Options, etc.), injection-safe Pydantic models, ownership enforcement on self-scoped routes
- **PostHog analytics** — opt-in via `VITE_POSTHOG_API_KEY`
- **Sentry error monitoring** — backend + frontend, configurable via DSN env vars
- **Admin dashboard** — separate React app (`frontendAdmin/`) at port 3001; user management (ban/unban), activity view, Sentry error log, user feedback inbox, reported conversation moderation, admin-only recompute endpoint

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | MongoDB (Motor async driver) |
| Auth | JWT (python-jose, HS256), bcrypt |
| Frontend | React 18 (Vite), plain JSX, Axios |
| Admin UI | React 18 (Vite), separate app in `frontendAdmin/` |
| File storage | Cloudinary (photos) |
| Testing | pytest 8.3.5, pytest-asyncio 0.26.0 (both pinned — see [Running Tests](#running-tests)), FastAPI TestClient, httpx |
| Rate limiting | slowapi, Upstash Redis (in-memory fallback) |
| Monitoring | Sentry (backend + frontend), PostHog (frontend) |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running on `localhost:27017`

---

## Installation & Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd Matching
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
```

> **Re-run `pip install -r requirements.txt` after every pull, not just on first setup.** The test tooling is version-pinned and the pins changed on 2026-09-03 (`pytest` 7.4.4 → 8.3.5, `pytest-asyncio` 0.23.3 → 0.26.0). An environment still on the old versions does not error — it fails in a way that looks like broken application code. See [Running Tests](#running-tests).

Copy `.env.example` to `.env` and fill in values (see Environment Variables below), then start:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

**Run the index migration** against your MongoDB instance — required on a fresh clone, and again after any pull that adds a collection:

```bash
python migrate_indexes.py
```

The script is idempotent and safe to re-run: existing indexes are skipped, not recreated. Skipping it fails silently rather than loudly — nothing errors, but the newer collections have no indexes at all, so every group and invite lookup does a full collection scan and **pending group invites never expire**, since that 14-day expiry is enforced by the `group_invites` partial TTL index and nothing else.

Each environment needs its own run; migrating locally does nothing for a deployed database.

### 3. Main Frontend

```bash
cd frontendv2
npm install
npm run dev
```

Frontend: `http://localhost:3000`

### 4. Admin Frontend

```bash
cd frontendAdmin
npm install
npm run dev
```

Admin dashboard: `http://localhost:3001` — requires an account whose ID is listed in `ADMIN_USER_IDS`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `"dev-secret-key"` | JWT signing secret — **required in production** (app raises `RuntimeError` if absent) |
| `MONGO_URL` | `"mongodb://localhost:27017"` | MongoDB connection URI |
| `MONGO_DB_NAME` | `"roommatch"` | MongoDB database name |
| `FRONTEND_URL` | `"http://localhost:3000"` | Allowed CORS origin for the main app |
| `ADMIN_FRONTEND_URL` | _(none)_ | Allowed CORS origin for the admin dashboard |
| `ADMIN_USER_IDS` | _(none)_ | Comma-separated integer user IDs that have admin access |
| `CLOUDINARY_CLOUD_NAME` | _(none)_ | Cloudinary cloud name for photo uploads |
| `CLOUDINARY_API_KEY` | _(none)_ | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | _(none)_ | Cloudinary API secret |
| `SENTRY_DSN` | _(none — Sentry disabled)_ | Backend Sentry project DSN |
| `SENTRY_AUTH_TOKEN` | _(none)_ | Sentry API token (needed for admin Errors page) |
| `SENTRY_ORG` | _(none)_ | Sentry org slug (needed for admin Errors page) |
| `SENTRY_PROJECT` | _(none)_ | Sentry project slug (needed for admin Errors page) |
| `UPSTASH_REDIS_REST_URL` | _(none — in-memory fallback)_ | Upstash Redis REST URL for rate limit state |
| `UPSTASH_REDIS_REST_TOKEN` | _(none)_ | Upstash Redis token |
| `ROOMMATCH_ENV` | `"development"` | Set to `"production"` on Render |
| `SENDGRID_API_KEY` | _(none)_ | SendGrid key — email delivery not yet wired (P3FT.2) |

### Main Frontend (`frontendv2/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API base URL (e.g. `https://yourapp.onrender.com/api`) |
| `VITE_ENV` | Set to `"production"` on Vercel |
| `VITE_SENTRY_DSN` | Frontend Sentry project DSN |
| `VITE_POSTHOG_API_KEY` | PostHog project API key (analytics; omit to disable) |

### Admin Frontend (`frontendAdmin/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API base URL |

---

## Database

MongoDB database: `roommatch` (configurable via `MONGO_DB_NAME`)

| Collection | Description |
|-----------|-------------|
| `users` | User profiles, preferences, hashed passwords, status flags |
| `likes` | Like records between users |
| `matches` | Confirmed mutual matches |
| `recommendations` | Pre-computed match recommendations per user |
| `chat_messages` | Chat message history |
| `notifications` | In-app notifications |
| `blocks` | Block records between users |
| `reports` | User reports (moderation queue) |
| `feedback` | User-submitted feedback messages |
| `conversation_reports` | Reported chat conversations (moderation queue) |
| `chat_read_status` | Per-user-per-conversation last-read timestamps |
| `swipes` | Skip records with 30-day TTL |
| `groups` | Roommate groups (2–4 same-gender members) |
| `group_invites` | Group invitations; **pending** invites expire after 14 days via a partial TTL index — accepted and declined invites are retained permanently |
| `outcomes` | Roommate-pairing outcomes, kept for tuning scoring weights; `userId` and `partnerId` are nullable (account erasure anonymizes these rows rather than deleting them) |
| `counters` | Atomic ID generation counter |

Schema notes for `groups`, `group_invites`, and `outcomes` are documented inline in `backend/app/database.py`.

---

## Key API Endpoints

Full interactive docs at `/docs` when running locally.

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register (returns access + refresh tokens) |
| `POST` | `/api/auth/login` | Login (returns access + refresh tokens) |
| `GET` | `/api/auth/me` | Current user (requires auth) |
| `POST` | `/api/auth/refresh` | Rotate refresh token |
| `POST` | `/api/auth/logout` | Invalidate refresh token server-side |
| `POST` | `/api/auth/change-password` | Change password (requires current password) |
| `POST` | `/api/auth/forgot-password` | Request password reset token |
| `POST` | `/api/auth/reset-password` | Reset password with token |
| `POST` | `/api/auth/restore-account` | Restore soft-deleted account |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{id}` | Get profile |
| `PUT` | `/api/users/{id}` | Update profile |
| `DELETE` | `/api/users/{id}` | Soft-delete account |
| `POST` | `/api/users/{id}/like` | Like a user |
| `DELETE` | `/api/users/{id}/like/{liked_id}` | Cancel a pending like |
| `POST` | `/api/users/{id}/skip/{skipped_id}` | Skip/pass on a user (30-day TTL) |
| `GET` | `/api/users/{id}/top-matches` | Recommended profiles (housing-filtered, move-in-penalized); 8 optional filter params |
| `GET` | `/api/profile-prompts` | Prompt catalogue (public — signup needs it pre-auth) |
| `POST` | `/api/users/{id}/notifications/{notification_id}/mark-read` | Mark one notification read |
| `GET` | `/api/users/{id}/match-breakdown/{other_id}` | Per-category compatibility breakdown |
| `POST` | `/api/users/{id}/roommate-found` | Mark that you found a roommate |
| `POST` | `/api/users/{id}/roommate-found/undo` | Clear roommate-found status |
| `GET` | `/api/users/{id}/matches` | Confirmed matches |
| `POST` | `/api/users/{id}/unmatch` | Unmatch |
| `GET` | `/api/users/{id}/likes-received` | Incoming likes |
| `GET` | `/api/users/{id}/likes-sent` | Outgoing pending likes |
| `POST` | `/api/users/{id}/upload-photo` | Upload profile photo |
| `POST` | `/api/users/{id}/block/{target_id}` | Block a user |
| `POST` | `/api/users/{id}/unblock/{target_id}` | Unblock a user |
| `POST` | `/api/users/{id}/report/{reported_id}` | Report a user |
| `POST` | `/api/users/{id}/pause` | Hide profile from discover |
| `POST` | `/api/users/{id}/unpause` | Restore profile to discover |
| `POST` | `/api/users/{id}/deactivate` | Deactivate account (requires password) |
| `POST` | `/api/users/{id}/reactivate` | Reactivate account |
| `POST` | `/api/users/{id}/accept-terms` | Record ToS acceptance |
| `POST` | `/api/users/{id}/submit-age` | Submit date of birth |
| `GET` | `/api/users/{id}/export-data` | GDPR data export (JSON) |

### Groups

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/groups` | Create a group with yourself as first member |
| `GET` | `/api/groups/mine` | Your group plus your pending invites — returns `{group, pendingInvites}` |
| `POST` | `/api/groups/{group_id}/invite/{user_id}` | Invite a match of an existing member |
| `POST` | `/api/groups/{group_id}/invites/{invite_id}/respond` | Accept or decline — body `{action}` |
| `POST` | `/api/groups/{group_id}/leave` | Leave the group |
| `DELETE` | `/api/groups/{group_id}` | Disband (creator, or last remaining member) |
| `GET` | `/api/groups/{group_id}/compatibility` | Pairwise scores as `matrix` + `pairs`, with mean and weakest pair |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{id}/chat/conversations` | List conversations |
| `GET` | `/api/users/{id}/chat/{partner_id}` | Get messages + partner last-read time; optional `after` (ISO-8601; percent-encode `+00:00` or use `Z`) |
| `POST` | `/api/users/{id}/chat/{partner_id}` | Send message |
| `POST` | `/api/chat/{partner_id}/mark-read` | Mark conversation read |
| `GET` | `/api/users/{id}/unread-chats` | Unread count + partner IDs |
| `POST` | `/api/chat/{partner_id}/report` | Report a conversation |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/admin/recompute` | Recompute all recommendations |
| `GET` | `/api/admin/users` | List all users |
| `GET` | `/api/admin/users/{id}/activity` | User activity (matches, likes, chats) |
| `POST` | `/api/admin/ban/{user_id}` | Ban a user |
| `POST` | `/api/admin/unban/{user_id}` | Unban a user |
| `GET` | `/api/admin/errors` | Sentry error log proxy |
| `GET` | `/api/admin/feedback` | User feedback inbox |
| `GET` | `/api/admin/reports` | Conversation reports queue |
| `POST` | `/api/admin/reports/{id}/resolve` | Resolve a conversation report |

---

## Project Structure

```
Matching/
├── backend/
│   ├── app/
│   │   ├── auth/
│   │   │   ├── utils.py               # bcrypt, JWT encode/decode, age check
│   │   │   └── dependencies.py        # get_current_user, get_admin_user, verify_match_exists
│   │   ├── routers/
│   │   │   ├── authRoutes.py          # /api/auth/* endpoints
│   │   │   ├── groupRoutes.py         # /api/groups/* endpoints
│   │   │   ├── matchingRoutes.py      # /api/matchScore, /uploadUsers, /match
│   │   │   └── userRoutes.py          # /api/users/*, /api/admin/*, /api/chat/* endpoints
│   │   ├── services/
│   │   │   ├── blockService.py        # block/unblock logic
│   │   │   ├── groupService.py        # group lifecycle, invites, cascades
│   │   │   ├── likeService.py         # like → match flow
│   │   │   ├── matchScore.py          # Weighted scoring, deal-breakers, category breakdown
│   │   │   ├── recommendationService.py  # Top-N recommendations, housing filters
│   │   │   ├── roommateService.py     # "Found a roommate" status + outcome records
│   │   │   └── userProfileService.py
│   │   ├── models.py                  # Pydantic request/response models
│   │   ├── database.py                # Motor MongoDB collection handles + schema notes
│   │   ├── limiter.py                 # slowapi Limiter (token-keyed, Redis-optional)
│   │   └── main.py                    # FastAPI app, middleware, lifespan
│   ├── tests/                         # 745 pytest tests (734 passing)
│   ├── migrate_indexes.py             # Idempotent index creation (run once per environment)
│   └── requirements.txt
├── frontendv2/
│   ├── src/
│   │   ├── context/AuthContext.jsx    # JWT-aware auth state, refresh token handling
│   │   ├── pages/                     # 16 page components (incl. GroupPage at /group)
│   │   ├── components/                # 11 shared components (SliderPicker, Toggle, Modal,
│   │   │                              #   NotificationBell, Spinner, LegalModal, HousingFields,
│   │   │                              #   HousingSummary, ScoreBreakdown, RoommateFoundBanner,
│   │   │                              #   RoommateFoundModal)
│   │   ├── styles/                    # 27 CSS files (one per page/component)
│   │   ├── test/setup.js              # Vitest + RTL setup
│   │   ├── *.test.js(x)               # 154 Vitest tests colocated with source
│   │   ├── services/api.js            # Axios client with Bearer + 401 refresh interceptor
│   │   └── utils/                     # theme.js, categories.js, housing.js, breakdown.js,
│   │                                  #   prompts.js, discoverFilters.js, profileOptions.js
│   └── package.json
├── frontendAdmin/
│   ├── src/
│   │   ├── context/AuthContext.jsx    # Admin auth (rejects non-admin on login)
│   │   ├── pages/                     # UserListPage, UserDetailPage, ErrorsPage, FeedbackPage, ReportsPage
│   │   ├── services/adminApi.js       # Admin-scoped Axios client
│   │   └── components/               # Sidebar, ConfirmDialog
│   └── package.json
├── docs/
│   ├── TASKS.md                       # Living task tracker
│   ├── summaries/                     # Per-agent feature summaries
│   ├── session-summaries/             # Per-sprint session summaries
│   └── security/                      # OWASP audit reports
└── README.md
```

---

## Running Tests

### Backend

```bash
cd backend
pip install -r requirements.txt   # required if you have not installed since 2026-09-03
pytest tests/ -v
```

745 tests covering auth, password security, rate limiting, IDOR/ownership enforcement, photo upload, Pydantic validation, MongoDB injection, CORS, security headers, match scoring, chat read receipts, cancel like, profile pause/deactivate, skip, housing intent, score breakdown, roommate-found status, roommate groups, profile prompts, discover filters, and the cleanup regressions.

Expect **734 passing and 11 failing**. The 11 are known, tracked in [docs/TASKS.md](docs/TASKS.md), and are test-side issues rather than environment problems — the failure set is deterministic and byte-identical across runs. A different count, or a collection error before any test runs, means something is wrong with your setup.

### Test tooling is version-pinned — install before you debug

`pytest==8.3.5` and `pytest-asyncio==0.26.0` in `requirements.txt` are load-bearing, not incidental.

`backend/pytest.ini` sets `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope`, and **both options require `pytest-asyncio >= 0.26`** — not 0.24, as the changelog implies. On older versions they are not rejected: pytest only *warns* about unknown ini keys, so the options are silently ignored and every async test quietly runs on its own event loop. The suite then fails in ways that read as broken application code.

`backend/tests/conftest.py` asserts the installed version so a stale environment fails loudly with a clear message instead of degrading. If you see that assertion, run `pip install -r requirements.txt` — do not work around it.

Two files in `backend/tests/` are excluded from collection by design: `test_api.py` and `test_api_v2.py` are manual scripts that require a live server. Run them by hand against a running backend.

Each pytest run uses its own database, named `roommatch_test_<pid>` and dropped at session teardown, so two suites running at once cannot delete each other's fixtures. Set `ROOMMATCH_TEST_DB` to pin a stable name while debugging a run — it can only name a database starting with `roommatch_test`, so it cannot be pointed at real data.

### Frontend

```bash
cd frontendv2
npm install
npm test              # also: npm run test:watch, npm run test:coverage
```

154 tests (Vitest + React Testing Library, jsdom) covering `AuthContext`, the `api.js` service layer including the real request/response interceptors, the discover-filter and prompt utilities, and the like/match UI flow on `DiscoverPage`. All network calls are mocked; no running backend is required.

---

## Security Notes

- Passwords hashed with bcrypt (rounds=12); never stored or returned in plain text
- JWT access tokens expire after 24 hours; refresh tokens rotate every 30 days and can be invalidated server-side
- `SECRET_KEY` is required in production — app raises `RuntimeError` at startup if absent
- All routes except auth endpoints require a valid Bearer token. Ownership is enforced via `get_current_user_or_403` on self-scoped resources — profile writes, likes, chat, notifications, and data export — so one user cannot act on another's. Profile *reads* are deliberately open to any authenticated user, since Discover, Matches, and UserDetail exist to show other people's profiles; that is a design decision, not an oversight of the ownership check
- CORS is locked to `FRONTEND_URL` (not `*`) in production
- Security headers: HSTS, CSP (no `unsafe-inline`), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- Photo uploads: magic bytes validation, EXIF stripping via Pillow, dimension checks, UUID filenames, Cloudinary storage
- Full OWASP Top 10 (2021) audit at `docs/security/SECURITY_AUDIT_FINAL.md`
- Open security and hardening items are tracked in [docs/TASKS.md](docs/TASKS.md). The audit above reflects the codebase as of its date and is not a continuous guarantee.
