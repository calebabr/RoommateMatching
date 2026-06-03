import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

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
import RestoreAccountPage  from './pages/RestoreAccountPage';

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
    <div className="app-shell">

      {/* Backdrop (mobile only) */}
      {isMobile && sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={`sidebar ${isMobile ? '' : 'sidebar--desktop'}`}
        style={{
          position:   isMobile ? 'fixed' : 'relative',
          left:       isMobile ? (sidebarOpen ? 0 : -(sidebarW + 20)) : 0,
          width:      sidebarW,
          zIndex:     isMobile ? 50 : 'auto',
          boxShadow:  isMobile && sidebarOpen ? '6px 0 32px rgba(0,0,0,0.4)' : 'none',
        }}
      >

        {/* Logo row */}
        <div className={`sidebar-logo-row ${collapsed && !isMobile ? 'sidebar-logo-row--collapsed' : 'sidebar-logo-row--expanded'}`}>
          {collapsed && !isMobile ? (
            <span style={{ fontSize: 26 }}>🏠</span>
          ) : (
            <div className="sidebar-brand">
              <span style={{ fontSize: 26 }}>🏠</span>
              <span className="sidebar-brand-name">RoomMatch</span>
            </div>
          )}

          {/* Desktop collapse toggle */}
          {!isMobile && (
            <button
              className="sidebar-icon-btn sidebar-collapse-btn"
              onClick={() => setCollapsed(c => !c)}
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? '›' : '‹'}
            </button>
          )}

          {/* Mobile close button */}
          {isMobile && (
            <button
              className="sidebar-icon-btn sidebar-close-btn"
              onClick={() => setSidebarOpen(false)}
            >
              ✕
            </button>
          )}
        </div>

        {/* Nav items */}
        <nav className="sidebar-nav">
          {tabs.map(tab => {
            const active =
              location.pathname === tab.path ||
              (tab.path === '/chat' && location.pathname.startsWith('/chat'));
            const iconOnly = collapsed && !isMobile;
            return (
              <button
                key={tab.path}
                className={`sidebar-nav-item ${iconOnly ? 'sidebar-nav-item--collapsed' : 'sidebar-nav-item--expanded'} ${active ? 'sidebar-nav-item--active' : 'sidebar-nav-item--inactive'}`}
                onClick={() => { navigate(tab.path); if (isMobile) setSidebarOpen(false); }}
                title={iconOnly ? tab.label : undefined}
              >
                <span className="sidebar-nav-icon">{TAB_ICONS[tab.label]}</span>
                {!iconOnly && tab.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* ── Main content ── */}
      <main className="app-main">

        {/* Mobile top bar */}
        {isMobile && (
          <div className="mobile-topbar">
            <button
              className="mobile-topbar-menu-btn"
              onClick={() => setSidebarOpen(true)}
            >
              ☰
            </button>
            <span className="mobile-topbar-brand">🏠 RoomMatch</span>
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
      <div className="app-loading">
        <div className="app-loading-inner">
          <span style={{ fontSize: 56 }}>🏠</span>
          <p className="app-loading-name">RoomMatch</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login"           element={<LoginPage />} />
        <Route path="/signup"          element={<SignupPage />} />
        <Route path="/forgot-password"   element={<ForgotPasswordPage />} />
        <Route path="/reset-password"    element={<ResetPasswordPage />} />
        <Route path="/restore-account"   element={<RestoreAccountPage />} />
        <Route path="*"                  element={<Navigate to="/login" replace />} />
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
