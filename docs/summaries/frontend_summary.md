# RoomMatch Frontend Summary

## 1. Current State

A fully functional React SPA. All core features are implemented: auth (login/signup), profile management, roommate discovery with compatibility scoring, likes/matching, real-time-polled chat, and notifications. The UI is dark-themed, mobile-responsive (collapsible sidebar + hamburger menu), and uses no CSS framework — all inline styles.

## 2. Key Files

| Path | Role |
|------|------|
| `src/App.jsx` | Router setup, `SidebarLayout` (nav + responsive shell), `AppRoutes` (auth guard) |
| `src/context/AuthContext.jsx` | Global auth state; JWT stored in localStorage under `token`; user object cached under `roommatch_user`; exposes `user`, `token`, `loading`, `login`, `signup`, `logout`, `refreshUser`, `setUser` |
| `src/services/api.js` | Centralized Axios client; configurable base URL (default `http://localhost:8000/api`, overridable via `localStorage.getItem('roommatch_api_base')` or `setApiBase(url)`); attaches JWT on every request; clears `token` and `roommatch_user` then redirects to `/login` on 401; all exported API functions |
| `src/utils/theme.js` | `Colors` and `Radius` constants used for all styling |
| `src/utils/categories.js` | 9 preference categories (sleep, cleanliness, noise, etc.), 15 lifestyle tags, compatibility color/label helpers |
| `src/pages/` | 10 page components (see routes below) |
| `src/components/` | 5 shared components: `SliderPicker`, `Toggle`, `Modal`, `NotificationBell`, `Spinner` |

## 3. Pages & Routes

| Route | Page | Purpose |
|-------|------|---------|
| `/login` | `LoginPage` | Email/password login; configurable backend URL |
| `/signup` | `SignupPage` | 3-step wizard: basic info → preferences → lifestyle tags |
| `/profile` | `ProfilePage` | View/edit own profile, preferences, photo, bio, tags; delete account |
| `/discover` | `DiscoverPage` | Grid of top recommended profiles with scores; send likes |
| `/likes` | `LikesPage` | Incoming likes; like back to create a match |
| `/matches` | `MatchesPage` | Confirmed matches; preference comparison; navigate to chat |
| `/chat` | `ChatListPage` | List of active conversations with last message preview |
| `/chat/:partnerId` | `ChatPage` | Full chat thread; polls every 3s; Enter-to-send; unmatch from here |
| `/user/:userId` | `UserDetailPage` | Public profile view with compatibility score and like button |
| `/notifications` | `NotificationsPage` | Activity feed (likes, matches, unmatches); marks read on open |

Unauthenticated users (where `user` is null and loading is false) are redirected to `/login` by `AppRoutes`. When a user reaches max matches (5), Discover and Likes tabs are hidden from the sidebar.

## 4. API Integration

All calls go through `src/services/api.js` via a single Axios instance. The base URL defaults to `http://localhost:8000/api` but reads `localStorage.getItem('roommatch_api_base')` first; the exported `setApiBase(url)` function allows runtime override.

| Category | Functions | Called From |
|----------|-----------|-------------|
| Auth | `authLogin`, `authRegister`, `authMe` | AuthContext, LoginPage, SignupPage |
| User CRUD | `getUser`, `updateUser`, `deleteUser`, `uploadPhoto`, `getPhotoUrl` | ProfilePage, most pages (profile enrichment) |
| Recommendations | `getTopMatches` | DiscoverPage |
| Likes/Matching | `sendLike`, `getLikesReceived`, `getLikesSent`, `getMatches`, `unmatchUser` | DiscoverPage, LikesPage, MatchesPage, ChatPage, UserDetailPage |
| Match Score | `getMatchScore` | MatchesPage, UserDetailPage |
| Chat | `getChatConversations`, `getChatMessages`, `sendChatMessage` | ChatListPage, ChatPage |
| Notifications | `getNotifications`, `getUnreadNotificationCount`, `markNotificationsRead` | NotificationsPage, NotificationBell |

## 5. Gaps / TODOs

- **Chat is polling-based** (3s interval in `ChatPage`, 5s in `NotificationBell`). No WebSocket or SSE — will scale poorly.
- **No password reset / forgot-password flow.**
- **Gender is binary** (male/female only) — hardcoded in `SignupPage`.
- **`UserDetailPage` like button** uses a stale `profile.matched` flag from the fetched profile, not from the current user's match state — can show Like button incorrectly when user is already matched with that person.
- **No pagination** on discover, likes, matches, or chat history — all fetched at once.
- **Notification bell** polls every 5s globally and does not stop when the user is on the Notifications page (redundant API calls).
- **No email verification** step in signup.
- **Backend URL setting** is only accessible from the login screen; no way to change it once logged in.

## 6. Notable Patterns

- **Styling**: All inline styles using shared `Colors`/`Radius` constants from `utils/theme.js`; local `const S = {...}` style objects defined at the bottom of each file.
- **State**: React Context for auth only; all page-level state is local `useState`. No Redux or Zustand.
- **Routing**: React Router v6 nested routes; `SidebarLayout` renders `<Outlet />` for child pages.
- **Auth guard**: Implemented directly in `AppRoutes` — if `user` is null (and not loading), only `/login` and `/signup` are rendered.
- **Data enrichment pattern**: API returns IDs; pages resolve them to full profiles via parallel `Promise.all(getUser(...))` calls (Discover, Likes, Matches, ChatList).
- **Config**: Backend base URL is runtime-configurable via `setApiBase(url)` and persisted to localStorage under `roommatch_api_base`, useful for testing on physical devices.
- **Mobile-responsive sidebar**: hamburger menu and backdrop overlay on mobile; slide-in drawer on small screens; collapse toggle on desktop.
- **Auth session storage**: `saveSession`/`clearSession` in `AuthContext` manage two localStorage keys — `token` (JWT) and `roommatch_user` (cached user object). On 401, both are cleared before redirect.
