# RoomMatch Frontend Summary

## 1. Current State

A fully functional React SPA. All core features are implemented: auth (login/signup), profile management, roommate discovery with compatibility scoring, likes/matching, real-time-polled chat, and notifications. The UI is dark-themed, mobile-responsive (collapsible sidebar + hamburger menu), and uses no CSS framework — all inline styles.

## 2. Key Files

| Path | Role |
|------|------|
| `src/App.jsx` | Router setup, `SidebarLayout` (nav + responsive shell), `AppRoutes` (auth guard) |
| `src/context/AuthContext.jsx` | Global auth state; JWT stored in localStorage under `token`; user object cached under `roommatch_user`; exposes `user`, `token`, `loading`, `login`, `signup`, `logout`, `refreshUser`, `setUser` |
| `src/services/api.js` | Centralized Axios client; configurable base URL — reads `VITE_API_BASE_URL` at build time via `import.meta.env` (falls back to `http://localhost:8000/api`), further overridable at runtime via `localStorage.getItem('roommatch_api_base')` or `setApiBase(url)`; attaches JWT on every request; clears `token` and `roommatch_user` then redirects to `/login` on 401; all exported API functions |
| `src/utils/theme.js` | `Colors` and `Radius` constants used for all styling |
| `src/utils/categories.js` | 9 preference categories (sleep, cleanliness, noise, etc.), 15 lifestyle tags, compatibility color/label helpers |
| `src/pages/` | 12 page components (see routes below) |
| `src/components/` | 5 shared components: `SliderPicker`, `Toggle`, `Modal`, `NotificationBell`, `Spinner` |

## 3. Pages & Routes

| Route | Page | Purpose |
|-------|------|---------|
| `/login` | `LoginPage` | Email/password login; configurable backend URL; "Forgot password?" link below Sign In button; password show/hide toggle |
| `/signup` | `SignupPage` | 3-step wizard: basic info → preferences → lifestyle tags; password show/hide toggle on Step 1 |
| `/forgot-password` | `ForgotPasswordPage` | Email input; shows reset token in monospace box on success with dev-mode note; accessible without auth |
| `/reset-password` | `ResetPasswordPage` | Token input (pre-filled from `?token=` URL param) + new password with show/hide toggle; redirects to `/login` after 2s on success; accessible without auth |
| `/restore-account` | `RestoreAccountPage` | Public page; token input (pre-filled from `?token=` URL param); calls restore-account endpoint; accessible without auth |
| `/profile` | `ProfilePage` | View/edit own profile, preferences, photo, bio, tags; Blocked Users section; Danger Zone (export data, delete account with password modal + show/hide toggle + restore token notice) |
| `/discover` | `DiscoverPage` | Grid of top recommended profiles with scores; send likes |
| `/likes` | `LikesPage` | Incoming likes; like back to create a match |
| `/matches` | `MatchesPage` | Confirmed matches; preference comparison; navigate to chat |
| `/chat` | `ChatListPage` | List of active conversations with last message preview |
| `/chat/:partnerId` | `ChatPage` | Full chat thread; polls every 3s; Enter-to-send; unmatch from here |
| `/user/:userId` | `UserDetailPage` | Public profile view with compatibility score and like button; like button reflects current user's actual like/match state (P1.5); Block button with confirmation overlay; Report button with reason dropdown + description modal |
| `/notifications` | `NotificationsPage` | Activity feed (likes, matches, unmatches); marks read on open |

Unauthenticated users (where `user` is null and loading is false) are redirected to `/login` by `AppRoutes`. `/forgot-password`, `/reset-password`, and `/restore-account` are outside the auth guard and accessible without a token. When a user reaches max matches (5), Discover and Likes tabs are hidden from the sidebar.

## 4. API Integration

All calls go through `src/services/api.js` via a single Axios instance. The base URL defaults to `http://localhost:8000/api` but reads `localStorage.getItem('roommatch_api_base')` first; the exported `setApiBase(url)` function allows runtime override.

| Category | Functions | Called From |
|----------|-----------|-------------|
| Auth | `authLogin`, `authRegister`, `authMe`, `authForgotPassword`, `authResetPassword`, `restoreAccount` | AuthContext, LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage, RestoreAccountPage |
| User CRUD | `getUser`, `updateUser`, `deleteUser`, `uploadPhoto`, `getPhotoUrl`, `exportUserData` | ProfilePage, most pages (profile enrichment) |
| Recommendations | `getTopMatches` | DiscoverPage |
| Likes/Matching | `sendLike`, `getLikesReceived`, `getLikesSent`, `getMatches`, `unmatchUser` | DiscoverPage, LikesPage, MatchesPage, ChatPage, UserDetailPage |
| Match Score | `getMatchScore` | MatchesPage, UserDetailPage |
| Chat | `getChatConversations`, `getChatMessages`, `sendChatMessage` | ChatListPage, ChatPage |
| Notifications | `getNotifications`, `getUnreadNotificationCount`, `markNotificationsRead` | NotificationsPage, NotificationBell |
| Block | `blockUser`, `unblockUser`, `getBlockedUsers` | UserDetailPage, ProfilePage |
| Report | `reportUser` | UserDetailPage |
| Account deletion | `deleteAccount`, `exportUserData` | ProfilePage |

## 5. Gaps / TODOs

- **Chat is polling-based** (3s interval in `ChatPage`, 5s in `NotificationBell`). No WebSocket or SSE — will scale poorly.
- **Password reset token is shown in-browser** — `ForgotPasswordPage` displays the token returned by the API in a monospace box. No email delivery exists yet; users must copy the token manually. This is acceptable for MVP but must be replaced with email delivery before production launch.
- **Gender is binary** (male/female only) — hardcoded in `SignupPage`.
- ~~**`UserDetailPage` like button**~~ Fixed (P1.5, 2026-06-02): `canLike` now checks `alreadyLiked` and `alreadyMatched` state derived from `getLikesSent` and `user.matchedWith`, replacing the stale `profile.matched` flag.
- **No pagination** on discover, likes, matches, or chat history — all fetched at once.
- **Notification bell** polls every 5s globally and does not stop when the user is on the Notifications page (redundant API calls).
- **No email verification** step in signup.
- **Backend URL setting** is only accessible from the login screen; no way to change it once logged in.

## 6. Admin Dashboard App (`frontendAdmin/`)

**Session 2026-06-02 (Task P2.2):** A standalone React admin dashboard was built in `frontendAdmin/`. It runs on port 3001, uses its own `AuthContext`, and keeps all admin API calls in a dedicated service so it can be extracted or deployed independently.

### Auth flow

`frontendAdmin/src/context/AuthContext.jsx` stores the JWT in localStorage. On login, the response `is_admin` flag is checked — non-admin users are rejected immediately with an error message. The `App.jsx` auth guard redirects unauthenticated users to `/login`.

### Service layer

`frontendAdmin/src/services/adminApi.js` — centralized Axios client for all admin API calls. Attaches JWT on every request; redirects to `/login` on 401.

### Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/login` | `LoginPage` | Email/password login; rejects non-admin accounts |
| `/users` | `UserListPage` | Lists all users from `GET /api/admin/users`; search bar; status pills (active/banned) |
| `/users/:id` | `UserDetailPage` | User detail view; ban/unban button with `ConfirmDialog` |
| `/errors` | `ErrorsPage` | Placeholder for P3AD.1 (Sentry error log view) |
| `/feedback` | `FeedbackPage` | Placeholder for P3AD.2 (user feedback inbox) |

**Session 2026-06-02 (Task P3AD.3):** `UserDetailPage` was extended with an activity section; `adminApi.js` received a new function.

#### Activity section in `UserDetailPage`

An activity card was added below the existing user detail card. It contains three subsections:

| Subsection | Display |
|-----------|---------|
| Matches | Table: Name \| Matched Date |
| Likes Sent | Name pills (inline chips) |
| Chat Partners | Table: Name \| Messages \| Last Active |

The activity fetch (`adminGetUserActivity`) runs in parallel with the user fetch inside `useEffect`. Loading state shows `"Loading activity..."` and error state shows `"Could not load activity."` — both are self-contained and do not affect the rest of the page. Styling follows the existing card pattern.

#### `adminApi.js`

`adminGetUserActivity(userId)` added at the end of the service file. Calls `GET /api/admin/users/{userId}/activity` with the admin Bearer token.

### Components

| Component | Purpose |
|-----------|---------|
| `Sidebar.jsx` | Nav sidebar with links to Users, Errors, Feedback pages |
| `ConfirmDialog.jsx` | Modal confirmation prompt used by ban/unban actions |

### Configuration

| File | Purpose |
|------|---------|
| `frontendAdmin/.env.example` | Documents `VITE_API_BASE_URL` for this app |
| `frontendAdmin/vite.config.js` | Dev server on port 3001 |
| `frontendAdmin/package.json` | Dependencies: `axios ^1.6.0`, `react-router-dom ^6.0.0` |

---

## 8. Block System, Report System, Account Deletion UI, and Password Toggle

**Session 2026-06-03 (Tasks P2.20, P2.21, P2.22 UI + Password Toggle):**

### `RestoreAccountPage.jsx` (new, `/restore-account`)

Public page (no auth guard). Accepts a restore token — pre-filled from the `?token=` URL param if present. On submit calls `restoreAccount(token)`. Shows a success confirmation with a link to `/login` on 200; shows an error message on 400 (invalid or expired token).

### `UserDetailPage.jsx` — block and report controls

- **Block button**: renders a confirmation overlay before executing. After a successful block the user is navigated away to `/discover`. If the viewed user has already been blocked, the button label changes to "Unblock" and calls `unblockUser` instead.
- **Report button**: opens a modal with a 6-option reason `<select>` (`harassment`, `inappropriate_content`, `fake_profile`, `spam`, `underage`, `other`) and an optional `<textarea>` for description (max 1000 chars). On submit calls `reportUser`. Shows a success toast on 200 and an inline error on failure.

### `ProfilePage.jsx` — Blocked Users section and Danger Zone

- **Blocked Users section**: fetches and lists all users blocked by the current user (`getBlockedUsers`). Each entry shows the user's name with an Unblock button (`unblockUser`).
- **Danger Zone section**:
  - **Export Data** button: calls `exportUserData`; triggers a browser download of the response as `roommatch-data.json`.
  - **Delete Account** button: opens a modal requiring password re-entry. On confirm calls `deleteAccount`. On success the restore token is displayed in a monospace box with a note that the user has 7 days to restore the account, plus a link to `/restore-account`. The user is not immediately logged out — they must copy the token before the session ends.
  - Password field in the delete modal has a show/hide eye icon toggle (same pattern as other password fields).

### Password show/hide toggle (all pages)

An eye icon button is placed at the right edge of every password `<input>`. Clicking toggles the field's `type` between `"password"` and `"text"`. The toggle was added to:

| File | Field |
|------|-------|
| `frontendv2/src/pages/LoginPage.jsx` | Login password |
| `frontendv2/src/pages/SignupPage.jsx` | Signup password (Step 1) |
| `frontendv2/src/pages/ResetPasswordPage.jsx` | New password |
| `frontendv2/src/pages/ProfilePage.jsx` | Delete account modal password |
| `frontendAdmin/src/pages/LoginPage.jsx` | Admin login password |

---

## 9. CSS Migration and CSP Hardening (P3A.6 — 2026-06-03)

All inline styles driven by `utils/theme.js` `Colors` and `Radius` constants were migrated to external CSS files. This enabled removal of `'unsafe-inline'` from both `script-src` and `style-src` in the backend CSP.

### New files in `frontendv2/src/styles/` (21 total)

| File | Contents |
|------|----------|
| `theme.css` | CSS custom properties for all `Colors` and `Radius` values |
| `utilities.css` | Reusable utility classes (`bg-*`, `text-*`, `border-*`, layout) |
| `App.css` | App-level layout |
| `LoginPage.css` | Login page |
| `SignupPage.css` | Signup wizard |
| `ProfilePage.css` | Profile page |
| `DiscoverPage.css` | Discover grid |
| `LikesPage.css` | Likes page |
| `MatchesPage.css` | Matches page |
| `ChatListPage.css` | Chat list |
| `ChatPage.css` | Chat thread |
| `UserDetailPage.css` | Public profile view |
| `NotificationsPage.css` | Notifications feed |
| `ForgotPasswordPage.css` | Forgot-password page |
| `ResetPasswordPage.css` | Reset-password page |
| `RestoreAccountPage.css` | Restore-account page |
| `Modal.css` | Modal component |
| `SliderPicker.css` | Slider picker component |
| `Toggle.css` | Toggle component |
| `NotificationBell.css` | Notification bell component |
| `Spinner.css` | Spinner component |

### Migrated source files (18)

- `frontendv2/src/main.jsx` — imports all 21 CSS files
- `frontendv2/src/App.jsx` — static styles moved to `App.css`; sidebar position/width remain inline (JS state-driven)
- All 13 page files and all 5 component files — `style={{Colors.*}}` and `style={{Radius.*}}` replaced with `className`; `Radius` import removed from all files; `Colors` import removed where no longer needed

### Legitimate remaining inline styles

| File | Reason |
|------|--------|
| `Toggle.jsx` | Background is a JS conditional (`isOn ? colorA : colorB`) |
| `SliderPicker.jsx` | Gradient computed from a dynamic numeric value |
| `App.jsx` sidebar | Width and position driven by open/closed JS state |
| `MatchesPage.jsx`, `NotificationsPage.jsx`, `UserDetailPage.jsx` | Per-item colors derived from compatibility score |

### Impact on backend CSP

`backend/app/main.py` CSP updated: `'unsafe-inline'` removed from `style-src` and `script-src`. Both directives now only allow `'self'`.

---

## 10. Token Refresh Frontend (P3A.1 — 2026-06-03)

### `frontendv2/src/services/api.js`

Three localStorage helpers added (`saveRefreshToken`, `loadRefreshToken`, `clearRefreshToken`; key: `roommatch_refresh_token`) and two API functions (`authRefresh(refreshToken)`, `authLogout()`).

The previous simple 401-redirect interceptor was replaced with a **queued refresh interceptor**:
- On any 401, sets `_isRefreshing = true` and queues all in-flight requests in `_refreshQueue`
- Calls `authRefresh` with the stored refresh token
- On success: stores new tokens, replays every queued request with the new access token
- On failure: clears all tokens (`token`, `roommatch_user`, `roommatch_refresh_token`) and redirects to `/login`
- Guard: if the failing request is itself `/auth/refresh`, skips the refresh attempt to avoid an infinite loop

### `frontendv2/src/context/AuthContext.jsx`

- `login` and `signup` now call `saveRefreshToken(response.data.refresh_token)`
- `logout` is now `async`; calls `authLogout()` to invalidate the refresh token server-side before clearing localStorage

---

## 11. PostHog Product Analytics (P2.25 — 2026-06-03)

`posthog-js` was installed and wired across five frontend files. PostHog initializes in `main.jsx` only when `VITE_POSTHOG_API_KEY` is set (`capture_pageview: false`, `person_profiles: 'identified_only'`), so local dev with no key is a complete no-op.

### Initialization

`frontendv2/src/main.jsx` — guarded `posthog.init(import.meta.env.VITE_POSTHOG_API_KEY, { api_host: 'https://us.i.posthog.com', capture_pageview: false, person_profiles: 'identified_only' })` runs before `ReactDOM.createRoot`. No-op if the env var is absent.

### Identity management (`AuthContext.jsx`)

| Action | PostHog call |
|--------|-------------|
| `login()` success | `posthog.identify(user.id)` + `posthog.capture('login', { method: 'email' })` |
| `signup()` success | `posthog.identify(user.id)` + `posthog.capture('signup_completed')` |
| `logout()` | `posthog.capture('logout')` + `posthog.reset()` |

### Events by file

| File | Event | Trigger |
|------|-------|---------|
| `SignupPage.jsx` | `signup_started` | `onFocus` on the Email field (first field); fires exactly once per signup session via a `signupStartedFired` ref |
| `ProfilePage.jsx` | `photo_uploaded` | After successful photo upload response |
| `ProfilePage.jsx` | `profile_completed` | After successful profile save |
| `ProfilePage.jsx` | `account_deleted` | Immediately before calling `logout()` in `handleDeleteAccount` |
| `UserDetailPage.jsx` | `match_created` | In `handleLike()` when API returns `status === 'matched'`; payload `{ matched_user_id }` |
| `UserDetailPage.jsx` | `like_sent` | In `handleLike()` when API does not return `matched`; payload `{ target_user_id }` |
| `ChatPage.jsx` | `message_sent` | After successful `sendChatMessage` call in `handleSend` |

### Not yet implemented

- `profile_skipped` — requires the Skip button from P3FT.4
- `email_verified` — requires the SendGrid flow from P3FT.2

### Env var

`VITE_POSTHOG_API_KEY` (note: original spec said `VITE_POSTHOG_KEY` — the actual implementation uses `VITE_POSTHOG_API_KEY`). Set on the Vercel project under Environment Variables.

---

## 7. Notable Patterns

- **Styling**: CSS custom properties in `theme.css` replace the `Colors`/`Radius` JavaScript constants for static values. Dynamic/computed values (score-based colors, toggle state, slider gradients, sidebar dimensions) remain as inline styles where JavaScript logic drives the value.
- **State**: React Context for auth only; all page-level state is local `useState`. No Redux or Zustand.
- **Routing**: React Router v6 nested routes; `SidebarLayout` renders `<Outlet />` for child pages.
- **Auth guard**: Implemented directly in `AppRoutes` — if `user` is null (and not loading), only `/login`, `/signup`, `/forgot-password`, and `/reset-password` are rendered.
- **Data enrichment pattern**: API returns IDs; pages resolve them to full profiles via parallel `Promise.all(getUser(...))` calls (Discover, Likes, Matches, ChatList).
- **Config**: Backend base URL resolves in priority order: (1) `localStorage.getItem('roommatch_api_base')`, (2) `import.meta.env.VITE_API_BASE_URL` (set at Vite build time), (3) hard-coded fallback `http://localhost:8000/api`. The `setApiBase(url)` function writes to localStorage for runtime override, useful for testing on physical devices.
- **Sentry error monitoring**: `@sentry/react` initialized in `main.jsx` when `VITE_SENTRY_DSN` is set. Uses `VITE_ENV` for the environment tag; `tracesSampleRate` is 0.1 in production and 0.0 otherwise. A `beforeSend` hook replaces any captured `Authorization` header value with `"[Filtered]"` before the event is sent. No-op if `VITE_SENTRY_DSN` is unset.
- **Mobile-responsive sidebar**: hamburger menu and backdrop overlay on mobile; slide-in drawer on small screens; collapse toggle on desktop.
- **Auth session storage**: `saveSession`/`clearSession` in `AuthContext` manage two localStorage keys — `token` (JWT) and `roommatch_user` (cached user object). On 401, both are cleared before redirect.
