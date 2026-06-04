# RoomMatch

A roommate matching web application for Auburn University students. Users create profiles with lifestyle preferences, receive compatibility-scored recommendations, like and match with each other, and chat in real time.

For task tracking see [docs/TASKS.md](docs/TASKS.md).

---

## Features

- **Profile creation** — name, gender, bio, photo (Cloudinary), lifestyle preferences (sleep schedule, cleanliness, noise tolerance, guests, personality, smoking, shared space, communication), lifestyle tags, religion tag, major, graduation year/season
- **Soft profile prompts** — users missing major or graduation year are gently prompted to fill them in
- **Matching algorithm** — weighted preference comparison with deal-breaker logic in `matchScore.py`; gender-gated (same-gender only); max 5 matches per user
- **Likes / Matches** — like others, cancel pending likes, mutual like creates a match; unmatching supported
- **Skip / Pass** — pass on a discover profile; skipped users hidden for 30 days (`swipes` collection with TTL index)
- **Chat** — per-match conversation threads; iMessage-style read receipts ("Seen [time]"), unread badge on nav icon, "New messages" divider, relative timestamps
- **Notifications** — in-app notifications for new likes, matches, and messages
- **Age verification** — date of birth required at signup; under-18 accounts blocked
- **Terms of Service / Privacy Policy** — in-app modal on first login; versioned (`CURRENT_TERMS_VERSION` in `App.jsx`); in-app pages at `/terms` and `/privacy`
- **Account management** — pause profile (hidden from discover), deactivate account, soft-delete with 7-day restore window, GDPR data export, account restoration
- **Block & Report** — block/unblock users (auto-unmatch); report with reason; auto-block on report
- **Token refresh** — silent 30-day refresh token rotation; server-side logout invalidation
- **Rate limiting** — slowapi; public endpoints limited by IP, authenticated endpoints by user ID; Upstash Redis in production, in-memory fallback locally
- **Security** — bcrypt passwords, JWT (HS256, 24h access / 30d refresh), CORS locked to `FRONTEND_URL`, security headers (HSTS, CSP with no `unsafe-inline`, X-Frame-Options, etc.), injection-safe Pydantic models, IDOR ownership enforcement
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
| Testing | pytest, FastAPI TestClient, httpx |
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

Copy `.env.example` to `.env` and fill in values (see Environment Variables below), then start:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

**First-time DB setup** — run the index migration against your MongoDB instance:

```bash
python migrate_indexes.py
```

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
| `clusters` | User clusters for recommendation engine |
| `chat_messages` | Chat message history |
| `notifications` | In-app notifications |
| `feedback` | User-submitted feedback messages |
| `conversation_reports` | Reported chat conversations (moderation queue) |
| `chat_read_status` | Per-user-per-conversation last-read timestamps |
| `swipes` | Skip records with 30-day TTL |
| `counters` | Atomic ID generation counter |

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
| `GET` | `/api/users/{id}/top-matches` | Recommended profiles |
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

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{id}/chat/conversations` | List conversations |
| `GET` | `/api/users/{id}/chat/{partner_id}` | Get messages + partner last-read time |
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
│   │   │   └── userRoutes.py          # /api/users/*, /api/admin/*, /api/chat/* endpoints
│   │   ├── services/
│   │   │   ├── blockService.py        # block/unblock logic
│   │   │   ├── likeService.py         # like → match flow
│   │   │   └── userProfileService.py
│   │   ├── matchScore.py              # Weighted preference scoring with deal-breaker logic
│   │   ├── models.py                  # Pydantic request/response models
│   │   ├── database.py                # Motor MongoDB collection handles
│   │   ├── limiter.py                 # slowapi Limiter (token-keyed, Redis-optional)
│   │   └── main.py                    # FastAPI app, middleware, lifespan
│   ├── tests/                         # ~312 pytest tests
│   ├── migrate_indexes.py             # Idempotent index creation (run once per environment)
│   └── requirements.txt
├── frontendv2/
│   ├── src/
│   │   ├── context/AuthContext.jsx    # JWT-aware auth state, refresh token handling
│   │   ├── pages/                     # 13 page components
│   │   ├── components/                # SliderPicker, Toggle, Modal, NotificationBell, Spinner
│   │   ├── styles/                    # 21 CSS files (one per page/component)
│   │   ├── services/api.js            # Axios client with Bearer + 401 refresh interceptor
│   │   └── utils/                     # theme.js, categories.js
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

```bash
cd backend
pytest tests/ -v
```

~312 tests covering auth, password security, rate limiting, IDOR/ownership enforcement, photo upload, Pydantic validation, MongoDB injection, CORS, security headers, match scoring, chat read receipts, cancel like, profile pause/deactivate, skip, and more.

---

## Security Notes

- Passwords hashed with bcrypt (rounds=12); never stored or returned in plain text
- JWT access tokens expire after 24 hours; refresh tokens rotate every 30 days and can be invalidated server-side
- `SECRET_KEY` is required in production — app raises `RuntimeError` at startup if absent
- All routes except auth endpoints require a valid Bearer token; ownership is enforced via `get_current_user_or_403`
- CORS is locked to `FRONTEND_URL` (not `*`) in production
- Security headers: HSTS, CSP (no `unsafe-inline`), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- Photo uploads: magic bytes validation, EXIF stripping via Pillow, dimension checks, UUID filenames, Cloudinary storage
- Full OWASP Top 10 (2021) audit at `docs/security/SECURITY_AUDIT_FINAL.md`
