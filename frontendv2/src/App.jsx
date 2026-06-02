import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Colors, Radius } from './utils/theme';

import LoginPage          from './pages/LoginPage';
import SignupPage         from './pages/SignupPage';
import ProfilePage        from './pages/ProfilePage';
import DiscoverPage       from './pages/DiscoverPage';
import LikesPage          from './pages/LikesPage';
import MatchesPage        from './pages/MatchesPage';
import ChatListPage       from './pages/ChatListPage';
import ChatPage           from './pages/ChatPage';
import UserDetailPage     from './pages/UserDetailPage';
import NotificationsPage   from './pages/NotificationsPage';
import ForgotPasswordPage  from './pages/ForgotPasswordPage';
import ResetPasswordPage   from './pages/ResetPasswordPage';

const MAX_MATCHES = 5;
const MOBILE_BP   = 768;

const TAB_ICONS = { Profile: '👤', Discover: '🔍', Likes: '💌', Matches: '🤝', Chat: '💬' };

function SidebarLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const isFull = matchCount >= MAX_MATCHES;

  const [isMobile,    setIsMobile]    = useState(() => window.innerWidth < MOBILE_BP);
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= MOBILE_BP);
  const [collapsed,   setCollapsed]   = useState(false);

  useEffect(() => {
    const onResize = () => {
      const mobile = window.innerWidth < MOBILE_BP;
      setIsMobile(mobile);
      if (!mobile) setSidebarOpen(true);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const tabs = [
    { path: '/profile',  label: 'Profile'  },
    ...(!isFull ? [
      { path: '/discover', label: 'Discover' },
      { path: '/likes',    label: 'Likes'    },
    ] : []),
    { path: '/matches',  label: 'Matches'  },
    { path: '/chat',     label: 'Chat'     },
  ];

  const sidebarW = !isMobile && collapsed ? 64 : 220;

  return (
    <div style={{ display: 'flex', height: '100dvh', backgroundColor: Colors.bg, overflow: 'hidden', position: 'relative' }}>

      {/* Backdrop (mobile only) */}
      {isMobile && sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.55)', zIndex: 40 }}
        />
      )}

      {/* ── Sidebar ── */}
      <aside style={{
        position:        isMobile ? 'fixed' : 'relative',
        top:             0,
        bottom:          0,
        left:            isMobile ? (sidebarOpen ? 0 : -(sidebarW + 20)) : 0,
        width:           sidebarW,
        zIndex:          isMobile ? 50 : 'auto',
        flexShrink:      0,
        backgroundColor: Colors.bgCard,
        borderRight:     `1px solid ${Colors.border}`,
        display:         'flex',
        flexDirection:   'column',
        transition:      'left 0.26s ease, width 0.2s ease',
        overflow:        'hidden',
        boxShadow:       isMobile && sidebarOpen ? '6px 0 32px rgba(0,0,0,0.4)' : 'none',
      }}>

        {/* Logo row */}
        <div style={{
          padding: '18px 14px 16px',
          borderBottom: `1px solid ${Colors.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed && !isMobile ? 'center' : 'space-between',
        }}>
          {collapsed && !isMobile ? (
            <span style={{ fontSize: 26 }}>🏠</span>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 26 }}>🏠</span>
              <span style={{ fontSize: 18, fontWeight: 800, color: Colors.accent }}>RoomMatch</span>
            </div>
          )}

          {/* Desktop collapse toggle */}
          {!isMobile && (
            <button
              onClick={() => setCollapsed(c => !c)}
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              style={{ background: 'none', border: 'none', color: Colors.textMuted, cursor: 'pointer', fontSize: 15, padding: 4, lineHeight: 1, flexShrink: 0 }}
            >
              {collapsed ? '›' : '‹'}
            </button>
          )}

          {/* Mobile close button */}
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              style={{ background: 'none', border: 'none', color: Colors.textSecondary, cursor: 'pointer', fontSize: 22, padding: 4, lineHeight: 1 }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: '12px 8px', overflowY: 'auto' }}>
          {tabs.map(tab => {
            const active =
              location.pathname === tab.path ||
              (tab.path === '/chat' && location.pathname.startsWith('/chat'));
            const iconOnly = collapsed && !isMobile;
            return (
              <button
                key={tab.path}
                onClick={() => { navigate(tab.path); if (isMobile) setSidebarOpen(false); }}
                title={iconOnly ? tab.label : undefined}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: iconOnly ? 'center' : 'flex-start',
                  gap: iconOnly ? 0 : 12,
                  padding: iconOnly ? '12px 0' : '11px 14px',
                  borderRadius: Radius.md,
                  backgroundColor: active ? Colors.accentGlow : 'transparent',
                  border: `1px solid ${active ? Colors.accent + '40' : 'transparent'}`,
                  color: active ? Colors.accent : Colors.textSecondary,
                  fontSize: 15,
                  fontWeight: active ? 700 : 500,
                  cursor: 'pointer',
                  marginBottom: 6,
                  textAlign: 'left',
                  transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: 20 }}>{TAB_ICONS[tab.label]}</span>
                {!iconOnly && tab.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* ── Main content ── */}
      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Mobile top bar */}
        {isMobile && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 16px',
            backgroundColor: Colors.bgCard,
            borderBottom: `1px solid ${Colors.border}`,
            flexShrink: 0,
          }}>
            <button
              onClick={() => setSidebarOpen(true)}
              style={{ background: 'none', border: 'none', fontSize: 22, color: Colors.textPrimary, cursor: 'pointer', padding: 4, lineHeight: 1 }}
            >
              ☰
            </button>
            <span style={{ fontSize: 17, fontWeight: 800, color: Colors.accent }}>🏠 RoomMatch</span>
          </div>
        )}

        <Outlet />
      </main>
    </div>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ height: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.bg }}>
        <div style={{ textAlign: 'center' }}>
          <span style={{ fontSize: 56 }}>🏠</span>
          <p style={{ color: Colors.accent, fontWeight: 700, marginTop: 12, margin: '12px 0 0' }}>RoomMatch</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login"           element={<LoginPage />} />
        <Route path="/signup"          element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password"  element={<ResetPasswordPage />} />
        <Route path="*"                element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<SidebarLayout />}>
        <Route index                        element={<Navigate to="/profile" replace />} />
        <Route path="profile"               element={<ProfilePage />} />
        <Route path="discover"              element={<DiscoverPage />} />
        <Route path="likes"                 element={<LikesPage />} />
        <Route path="matches"               element={<MatchesPage />} />
        <Route path="chat"                  element={<ChatListPage />} />
        <Route path="chat/:partnerId"       element={<ChatPage />} />
        <Route path="user/:userId"          element={<UserDetailPage />} />
        <Route path="notifications"         element={<NotificationsPage />} />
        <Route path="*"                     element={<Navigate to="/profile" replace />} />
      </Route>
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
