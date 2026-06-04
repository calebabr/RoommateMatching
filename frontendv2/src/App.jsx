import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { submitAge, acceptTerms, submitFeedback } from './services/api';

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
import PrivacyPolicyPage   from './pages/PrivacyPolicyPage';
import TermsOfServicePage  from './pages/TermsOfServicePage';

const MAX_MATCHES = 5;
const MOBILE_BP   = 768;

const CURRENT_TERMS_VERSION = "2026-06-03";

const TERMS_CHANGELOG = {
  "2026-06-03": null, // Initial release — no changelog shown for first-time acceptance
};

function calculateAge(dobString) {
  const dob = new Date(dobString);
  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const m = today.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
  return age;
}

function AgeGateModal() {
  const { user, logout, refreshUser } = useAuth();
  const [dob, setDob] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [banMessage, setBanMessage] = useState('');

  const handleSubmit = useCallback(async () => {
    if (!dob) { setError('Please enter your date of birth.'); return; }
    if (calculateAge(dob) < 18) { setError('You must be at least 18 years old to use RoomMatch.'); return; }
    setError('');
    setLoading(true);
    try {
      const result = await submitAge(user.id, dob);
      if (result.status === 'banned') {
        setBanMessage(result.message || 'Your account has been banned for age policy violation.');
        setTimeout(() => logout(), 3000);
      } else {
        await refreshUser();
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [dob, user, logout, refreshUser]);

  const maxDate = new Date(new Date().setFullYear(new Date().getFullYear() - 18))
    .toISOString().split('T')[0];

  return (
    <div className="modal-overlay" style={{ zIndex: 10000 }}>
      <div className="modal-box">
        <p className="modal-title">Age Verification Required</p>
        {banMessage ? (
          <p className="modal-message" style={{ color: 'var(--color-danger)' }}>{banMessage}</p>
        ) : (
          <>
            <p className="modal-message">
              RoomMatch requires all users to be 18 or older. Please enter your date of birth to continue.
            </p>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6 }}>
                Date of Birth
              </label>
              <input
                className="form-input"
                type="date"
                value={dob}
                max={maxDate}
                onChange={e => { setDob(e.target.value); setError(''); }}
                style={{ width: '100%', boxSizing: 'border-box' }}
              />
              {error && (
                <p style={{ color: 'var(--color-danger)', fontSize: 13, marginTop: 6 }}>{error}</p>
              )}
            </div>
            <div className="modal-buttons">
              <button
                className="modal-btn modal-btn-primary"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? 'Submitting…' : 'Submit'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ToSModal() {
  const { user, refreshUser } = useAuth();
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isUpdate = TERMS_CHANGELOG[CURRENT_TERMS_VERSION] !== null;
  const changelog = TERMS_CHANGELOG[CURRENT_TERMS_VERSION];

  const handleAgree = useCallback(async () => {
    if (!agreed) return;
    setError('');
    setLoading(true);
    try {
      await acceptTerms(user.id, CURRENT_TERMS_VERSION);
      await refreshUser();
    } catch (err) {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [agreed, user, refreshUser]);

  return (
    <div className="modal-overlay" style={{ zIndex: 10000 }}>
      <div className="modal-box">
        {isUpdate && changelog && (
          <div style={{
            background: 'var(--color-warning-bg, rgba(232,168,56,0.15))',
            border: '1px solid var(--color-warning, #E8A838)',
            borderRadius: 8,
            padding: '10px 14px',
            marginBottom: 16,
            fontSize: 13,
            color: 'var(--color-text, #fff)',
          }}>
            <strong>Terms Updated</strong> — {changelog}
          </div>
        )}
        <p className="modal-title">
          {isUpdate ? 'Our Terms Have Been Updated' : 'Terms of Service'}
        </p>
        <p className="modal-message">
          Please review and accept our Terms of Service and Privacy Policy to continue using RoomMatch.
        </p>
        <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <a
            href="/terms"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--color-accent, #E8A838)', textDecoration: 'underline', fontSize: 14 }}
          >
            Terms of Service
          </a>
          <a
            href="/privacy"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--color-accent, #E8A838)', textDecoration: 'underline', fontSize: 14 }}
          >
            Privacy Policy
          </a>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
          <input
            id="tos-modal-agree"
            type="checkbox"
            checked={agreed}
            onChange={e => { setAgreed(e.target.checked); setError(''); }}
            style={{ marginTop: 3, accentColor: '#E8A838', width: 16, height: 16, flexShrink: 0, cursor: 'pointer' }}
          />
          <label
            htmlFor="tos-modal-agree"
            style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--color-text-secondary, #A0A0A0)', cursor: 'pointer' }}
          >
            I have read and agree to the Terms of Service and Privacy Policy
          </label>
        </div>
        {error && (
          <p style={{ color: 'var(--color-danger)', fontSize: 13, marginBottom: 12 }}>{error}</p>
        )}
        <div className="modal-buttons">
          <button
            className="modal-btn modal-btn-primary"
            onClick={handleAgree}
            disabled={!agreed || loading}
          >
            {loading ? 'Submitting…' : 'I Agree'}
          </button>
        </div>
      </div>
    </div>
  );
}

const TAB_ICONS = { Profile: '👤', Discover: '🔍', Likes: '💌', Matches: '🤝', Chat: '💬' };

const MAX_FEEDBACK_CHARS = 2000;

function FeedbackModal({ onClose }) {
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'error'

  const handleSubmit = useCallback(async () => {
    if (!message.trim()) return;
    setStatus('loading');
    try {
      await submitFeedback(message.trim());
      setStatus('success');
      setTimeout(() => onClose(), 2000);
    } catch {
      setStatus('error');
    }
  }, [message, onClose]);

  return (
    <div className="modal-overlay" style={{ zIndex: 10000 }}>
      <div className="modal-box" style={{ maxWidth: 480, width: '90%' }}>
        <p className="modal-title">Send Feedback</p>
        {status === 'success' ? (
          <p style={{ color: 'var(--color-success, #22aa55)', fontSize: 15, textAlign: 'center', padding: '8px 0' }}>
            Thanks for your feedback!
          </p>
        ) : (
          <>
            {status === 'error' && (
              <p style={{ color: 'var(--color-danger)', fontSize: 13, marginBottom: 10 }}>
                Something went wrong. Please try again.
              </p>
            )}
            <div style={{ marginBottom: 16 }}>
              <textarea
                className="form-input"
                placeholder="Describe the bug or share a suggestion..."
                value={message}
                onChange={e => setMessage(e.target.value.slice(0, MAX_FEEDBACK_CHARS))}
                rows={6}
                style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical', minHeight: 120 }}
              />
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', textAlign: 'right', marginTop: 4 }}>
                {message.length} / {MAX_FEEDBACK_CHARS}
              </p>
            </div>
            <div className="modal-buttons">
              <button
                className="modal-btn modal-btn-secondary"
                onClick={onClose}
                disabled={status === 'loading'}
              >
                Cancel
              </button>
              <button
                className="modal-btn modal-btn-primary"
                onClick={handleSubmit}
                disabled={!message.trim() || status === 'loading'}
              >
                {status === 'loading' ? 'Sending…' : 'Submit'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function SidebarLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const isFull = matchCount >= MAX_MATCHES;

  const [isMobile,       setIsMobile]       = useState(() => window.innerWidth < MOBILE_BP);
  const [sidebarOpen,    setSidebarOpen]    = useState(() => window.innerWidth >= MOBILE_BP);
  const [collapsed,      setCollapsed]      = useState(false);
  const [feedbackOpen,   setFeedbackOpen]   = useState(false);

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

          {/* Feedback button */}
          {(() => {
            const iconOnly = collapsed && !isMobile;
            return (
              <button
                className={`sidebar-nav-item ${iconOnly ? 'sidebar-nav-item--collapsed' : 'sidebar-nav-item--expanded'} sidebar-nav-item--inactive`}
                onClick={() => setFeedbackOpen(true)}
                title={iconOnly ? 'Send Feedback' : undefined}
                style={{ marginTop: 'auto' }}
              >
                <span className="sidebar-nav-icon">📝</span>
                {!iconOnly && 'Send Feedback'}
              </button>
            );
          })()}
        </nav>

        {/* Feedback modal */}
        {feedbackOpen && <FeedbackModal onClose={() => setFeedbackOpen(false)} />}
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
        <Route path="/privacy"           element={<PrivacyPolicyPage />} />
        <Route path="/terms"             element={<TermsOfServicePage />} />
        <Route path="*"                  element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  if (!user.dateOfBirth) {
    return <AgeGateModal />;
  }

  if (user.termsVersion !== CURRENT_TERMS_VERSION) {
    return <ToSModal />;
  }

  return (
    <>
      <Routes>
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms"   element={<TermsOfServicePage />} />
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
    </>
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
