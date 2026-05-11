import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Colors, Radius } from './utils/theme';

import LoginPage        from './pages/LoginPage';
import SignupPage       from './pages/SignupPage';
import ProfilePage      from './pages/ProfilePage';
import DiscoverPage     from './pages/DiscoverPage';
import LikesPage        from './pages/LikesPage';
import MatchesPage      from './pages/MatchesPage';
import ChatListPage     from './pages/ChatListPage';
import ChatPage         from './pages/ChatPage';
import UserDetailPage   from './pages/UserDetailPage';
import NotificationsPage from './pages/NotificationsPage';

const MAX_MATCHES = 5;

const TAB_ICONS = { Profile: '👤', Discover: '🔍', Likes: '💌', Matches: '🤝', Chat: '💬' };

function TabLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const isFull = matchCount >= MAX_MATCHES;

  const tabs = [
    { path: '/profile',  label: 'Profile'  },
    ...(!isFull ? [
      { path: '/discover', label: 'Discover' },
      { path: '/likes',    label: 'Likes'    },
    ] : []),
    { path: '/matches',  label: 'Matches'  },
    { path: '/chat',     label: 'Chat'     },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', backgroundColor: Colors.bg, maxWidth: 600, margin: '0 auto' }}>
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        <Outlet />
      </div>
      <nav style={{
        display: 'flex',
        backgroundColor: Colors.bgCard,
        borderTop: `1px solid ${Colors.border}`,
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        flexShrink: 0,
      }}>
        {tabs.map(tab => {
          const active = location.pathname === tab.path;
          return (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              style={{
                flex: 1,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                paddingTop: 10, paddingBottom: 10,
                border: 'none',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                opacity: active ? 1 : 0.5,
                gap: 3,
              }}
            >
              <span style={{ fontSize: active ? 22 : 18, transition: 'font-size 0.15s' }}>
                {TAB_ICONS[tab.label]}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 600,
                color: active ? Colors.accent : Colors.textMuted,
              }}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ height: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.bg }}>
        <div style={{ textAlign: 'center' }}>
          <span style={{ fontSize: 48 }}>🏠</span>
          <p style={{ color: Colors.accent, fontWeight: 700, marginTop: 12 }}>RoomMatch</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login"  element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="*"       element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<TabLayout />}>
        <Route index            element={<Navigate to="/profile" replace />} />
        <Route path="profile"   element={<ProfilePage />} />
        <Route path="discover"  element={<DiscoverPage />} />
        <Route path="likes"     element={<LikesPage />} />
        <Route path="matches"   element={<MatchesPage />} />
        <Route path="chat"      element={<ChatListPage />} />
      </Route>
      <Route path="/chat/:partnerId"  element={<ChatPage />} />
      <Route path="/user/:userId"     element={<UserDetailPage />} />
      <Route path="/notifications"    element={<NotificationsPage />} />
      <Route path="*"                 element={<Navigate to="/profile" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
