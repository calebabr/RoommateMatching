# RoomMatch

A roommate matching web application for Auburn University students. Users create profiles with lifestyle preferences (sleep schedule, cleanliness, noise tolerance, etc.), get compatibility-scored recommendations, like/match with each other, and chat.

## Architecture

- **Backend**: Python FastAPI app in `/backend`, async with Motor (MongoDB driver)
- **Frontend**: React (Vite) SPA in `/frontendv2`, using Axios for API calls
- **Database**: MongoDB (`roommatch` database on `localhost:27017`)
- **Auth**: JWT (HS256) via `python-jose`; tokens issued at login/register, stored in localStorage, sent as `Authorization: Bearer <token>`; `SECRET_KEY` env var required in production

## Key Technical Details

- Backend runs on port 8000, frontend on port 3000
- API routes are prefixed with `/api` — three routers: `authRoutes` (register, login, change-password), `matchingRoutes` (batch operations), `userRoutes` (CRUD, likes, chat, notifications)
- Match scoring uses weighted preference comparison with deal-breaker logic in `matchScore.py`
- Gender-gated matching: users only match with same gender
- Max 5 matches per user (`MAX_MATCHES = 5`)
- MongoDB collections: `users`, `likes`, `matches`, `recommendations`, `clusters`, `chat_messages`, `notifications`
- Frontend uses React Context (`AuthContext`) for user state, persisted to localStorage
- Photo uploads stored on Cloudinary (credentials via `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` env vars); legacy `/backend/uploads/` static serving retained for existing users

## Running

```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontendv2
npm run dev
```

## Code Style

- Backend: Python with Pydantic models, async/await for all DB operations
- Frontend: Functional React components with hooks, inline styles using a shared theme (`utils/theme.js`)
- No TypeScript — frontend is plain JSX
- API client centralized in `frontendv2/src/services/api.js`
