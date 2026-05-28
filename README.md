# RoomMatch

A roommate matching web application for Auburn University students. Users create profiles with lifestyle preferences, receive compatibility-scored recommendations, like and match with each other, and chat in real time.

---

## Features

### Authentication
- Register with email and password (bcrypt hashed, JWT issued on success)
- Login with email and password (returns JWT access token)
- All protected routes require a valid `Authorization: Bearer <token>` header
- Token rehydration on page load via `GET /api/auth/me`

### User Profiles
- Create and edit profiles: name, gender, bio, photo upload
- Lifestyle preference scores: sleep schedule (weekday/weekend), cleanliness, noise tolerance, guests, personality, smoking, shared space, communication
- Lifestyle tags (free-form labels)

### Matching
- Compatibility scoring via weighted preference comparison with deal-breaker logic
- Gender-gated matching (users only match with same gender)
- Maximum 5 matches per user
- Like other users; mutual like creates a match
- Unmatch at any time

### Recommendations
- Cluster-based recommendation engine pre-computes top matches per user
- Admin endpoint to trigger a full recompute

### Chat
- Per-match conversation threads
- Message history stored in MongoDB

### Notifications
- In-app notification system for new likes, matches, and messages

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | MongoDB (Motor async driver) |
| Auth | JWT (python-jose, HS256), bcrypt |
| Frontend | React 18 (Vite), plain JSX, Axios |
| Testing | pytest, FastAPI TestClient, httpx |

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

Set the JWT secret key (optional — defaults to a dev string):

```bash
# Windows PowerShell
$env:SECRET_KEY = "your-secret-key-here"

# macOS/Linux
export SECRET_KEY="your-secret-key-here"
```

**First-time only** — run the migration to backfill auth fields on any existing users:

```bash
python migrate_add_auth_fields.py
```

Start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontendv2
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `"dev-secret-key"` | JWT signing secret — change in production |

---

## API Reference

### Auth (public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user, returns JWT |
| `POST` | `/api/auth/login` | Login, returns JWT |
| `GET` | `/api/auth/me` | Get current user (requires auth) |

**Register / Login request body:**
```json
{
  "email": "user@auburn.edu",
  "password": "securepassword"
}
```

**Token response:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { ... }
}
```

### Users (all require `Authorization: Bearer <token>`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/all` | List all active users |
| `GET` | `/api/users/{id}` | Get user profile |
| `PUT` | `/api/users/{id}` | Update profile |
| `DELETE` | `/api/users/{id}` | Delete account |
| `POST` | `/api/users/{id}/like` | Like a user |
| `GET` | `/api/users/{id}/top-matches` | Get top match recommendations |
| `GET` | `/api/users/{id}/matches` | Get confirmed matches |
| `POST` | `/api/users/{id}/unmatch` | Unmatch a user |
| `GET` | `/api/users/{id}/likes-received` | Users who liked you |
| `GET` | `/api/users/{id}/likes-sent` | Users you liked |
| `POST` | `/api/users/{id}/upload-photo` | Upload profile photo |

### Chat (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{id}/chat/conversations` | List all conversations |
| `GET` | `/api/users/{id}/chat/{partner_id}` | Get messages with a user |
| `POST` | `/api/users/{id}/chat/{partner_id}` | Send a message |

### Notifications (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{id}/notifications` | Get notifications |
| `POST` | `/api/users/{id}/notifications/read` | Mark notifications read |

### Admin (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/admin/recompute` | Recompute all match recommendations |

---

## Database

MongoDB database: `roommatch` on `localhost:27017`

| Collection | Description |
|-----------|-------------|
| `users` | User profiles, preferences, hashed passwords |
| `likes` | Like records between users |
| `matches` | Confirmed mutual matches |
| `recommendations` | Pre-computed match recommendations |
| `clusters` | User clusters for recommendation engine |
| `chat_messages` | Chat message history |
| `notifications` | In-app notifications |

---

## Project Structure

```
Matching/
├── backend/
│   ├── app/
│   │   ├── auth/
│   │   │   ├── utils.py          # bcrypt hashing, JWT encode/decode
│   │   │   └── dependencies.py   # get_current_user FastAPI dependency
│   │   ├── routers/
│   │   │   ├── authRoutes.py     # /api/auth/* endpoints
│   │   │   ├── userRoutes.py     # /api/users/* endpoints
│   │   │   └── matchingRoutes.py # /api/match*, /api/matchScore
│   │   ├── services/
│   │   │   └── userProfileService.py
│   │   ├── models.py             # Pydantic models
│   │   ├── database.py           # Motor MongoDB connection
│   │   └── main.py               # FastAPI app, lifespan, router registration
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_auth.py          # 24 JWT auth tests
│   ├── migrate_add_auth_fields.py
│   └── requirements.txt
├── frontendv2/
│   ├── src/
│   │   ├── auth/
│   │   │   └── AuthContext.jsx   # JWT-aware auth context
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   └── SignupPage.jsx
│   │   └── services/
│   │       └── api.js            # Axios client with Bearer token interceptor
│   └── package.json
└── README.md
```

---

## Running Tests

```bash
cd backend
pytest tests/test_auth.py -v
```

24 tests covering registration, login, protected route access, duplicate detection, and end-to-end auth flows. All passing.

---

## Security Notes

- Passwords are hashed with bcrypt before storage — plain-text passwords are never persisted
- `hashed_password` is stripped from all API responses
- JWT tokens expire after 24 hours
- All routes except `/api/auth/register` and `/api/auth/login` require a valid token
- Set a strong `SECRET_KEY` environment variable before deploying to production
