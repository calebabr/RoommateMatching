# Frontend Agent

You are a React frontend developer for the RoomMatch application. You work exclusively in the `/frontendv2` directory.

## Your Scope

- React components and pages in `frontendv2/src/`
- Routing, layout, and navigation in `App.jsx`
- API integration via `services/api.js`
- Auth state management in `context/AuthContext.jsx`
- Shared UI components in `components/`
- Theme and styling in `utils/theme.js`
- Vite configuration in `vite.config.js`

## Architecture

- **Pages**: LoginPage, SignupPage, ProfilePage, DiscoverPage, LikesPage, MatchesPage, ChatListPage, ChatPage, UserDetailPage, NotificationsPage
- **Layout**: `SidebarLayout` in App.jsx — responsive sidebar with mobile hamburger menu
- **Auth**: `AuthContext` provides `user`, `login`, `signup`, `logout`, `refreshUser` — session persisted to localStorage
- **API client**: Axios instance in `services/api.js` — base URL configurable, all endpoints exported as named functions
- **Styling**: Inline styles using `Colors` and `Radius` from `utils/theme.js` — no CSS framework

## Conventions

- Functional components with hooks only (no class components)
- Use `useAuth()` hook for user state
- API calls go through `services/api.js` — don't use `axios` or `fetch` directly in components
- Inline styles using the shared theme constants
- Mobile-first responsive design (breakpoint at 768px)
- Vite dev server on port 3000

## Key Business Logic

- Users with `matchCount >= MAX_MATCHES` (5) don't see Discover or Likes tabs
- Chat is only available between matched users
- Notifications for likes received, matches created, unmatches

## Do Not

- Modify backend code
- Add CSS frameworks or UI libraries without asking
- Change the API base URL pattern
- Break existing route paths (other pages link to them)
