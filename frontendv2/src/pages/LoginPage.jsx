import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { setApiBase } from '../services/api';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

function EyeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email,     setEmail]     = useState('');
  const [password,  setPassword]  = useState('');
  const [serverUrl, setServerUrl] = useState(localStorage.getItem('roommatch_api_base') || 'http://localhost:8000/api');
  const [loading,   setLoading]   = useState(false);
  const [showServer, setShowServer] = useState(false);
  const [modal, setModal] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async (e) => {
    e?.preventDefault();
    if (!email.trim() || !password) { setModal({ title: 'Missing Fields', message: 'Please enter your email and password.' }); return; }
    setLoading(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Invalid email or password.';
      setModal({ title: 'Login Failed', message: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.page}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}
      <div style={S.scroll}>
        <div style={S.brand}>
          <span style={{ fontSize: 52 }}>🏠</span>
          <h1 style={S.title}>RoomMatch</h1>
          <p style={S.subtitle}>Find your perfect roommate</p>
        </div>

        <form style={S.card} onSubmit={handleLogin}>
          <p style={S.cardTitle}>Welcome Back</p>
          <p style={S.cardDesc}>Sign in to your account</p>

          <div style={S.inputGroup}>
            <label style={S.label}>Email</label>
            <input
              style={S.input}
              placeholder="you@example.com"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoFocus
            />
          </div>

          <div style={S.inputGroup}>
            <label style={S.label}>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                style={{ ...S.input, paddingRight: 40 }}
                placeholder="Enter your password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword(p => !p)}
                style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: '#888', display: 'flex', alignItems: 'center' }}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          <button type="submit" style={{ ...S.button, ...(loading ? S.buttonDisabled : {}) }} disabled={loading}>
            {loading ? <Spinner size={20} color={Colors.black} /> : 'Sign In'}
          </button>

          <div style={{ textAlign: 'right', margin: '8px 0 4px' }}>
            <Link to="/forgot-password" style={{ fontSize: 13, color: Colors.accent, textDecoration: 'none' }}>Forgot password?</Link>
          </div>

          <div style={S.divider}>
            <div style={S.dividerLine} />
            <span style={S.dividerText}>OR</span>
            <div style={S.dividerLine} />
          </div>

          <button type="button" style={S.secondaryButton} onClick={() => navigate('/signup')}>
            Create Account
          </button>
        </form>

        {import.meta.env.DEV && (
          <>
            <button style={S.serverToggle} onClick={() => setShowServer(s => !s)}>
              {showServer ? '▼' : '▸'} Server Settings
            </button>

            {showServer && (
              <div style={S.serverCard}>
                <label style={S.label}>Backend URL</label>
                <input
                  style={S.input}
                  placeholder="http://192.168.x.x:8000/api"
                  value={serverUrl}
                  onChange={e => { setServerUrl(e.target.value); setApiBase(e.target.value); }}
                />
                <p style={S.hint}>Use your machine's local IP when testing on a physical device</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const S = {
  page:   { height: '100dvh', backgroundColor: Colors.bg, overflowY: 'auto' },
  scroll: { maxWidth: 480, margin: '0 auto', padding: '0 24px 40px' },
  brand:  { textAlign: 'center', paddingTop: 60, marginBottom: 36 },
  title:  { fontSize: 34, fontWeight: 800, color: Colors.accent, letterSpacing: 1, margin: '12px 0 6px' },
  subtitle: { fontSize: 15, color: Colors.textSecondary, margin: 0 },
  card:   { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 24, border: `1px solid ${Colors.border}` },
  cardTitle: { fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 4px' },
  cardDesc:  { fontSize: 14, color: Colors.textSecondary, margin: '0 0 24px' },
  inputGroup: { marginBottom: 20 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: Colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.8 },
  input: {
    width: '100%', backgroundColor: Colors.bgInput,
    borderRadius: Radius.md, padding: '14px 16px',
    fontSize: 16, color: Colors.textPrimary,
    border: `1px solid ${Colors.border}`, outline: 'none',
  },
  button: {
    width: '100%', backgroundColor: Colors.accent,
    borderRadius: Radius.md, padding: '16px 0',
    fontSize: 16, fontWeight: 700, color: Colors.black,
    border: 'none', marginBottom: 4,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  buttonDisabled: { opacity: 0.6 },
  divider: { display: 'flex', alignItems: 'center', margin: '20px 0' },
  dividerLine: { flex: 1, height: 1, backgroundColor: Colors.border },
  dividerText: { margin: '0 14px', fontSize: 12, color: Colors.textMuted, fontWeight: 600 },
  secondaryButton: {
    width: '100%', backgroundColor: 'transparent',
    border: `1.5px solid ${Colors.accent}`,
    borderRadius: Radius.md, padding: '14px 0',
    fontSize: 16, fontWeight: 600, color: Colors.accent,
  },
  serverToggle: {
    display: 'block', margin: '28px auto 0',
    background: 'none', border: 'none',
    fontSize: 13, color: Colors.textMuted, cursor: 'pointer',
  },
  serverCard: {
    backgroundColor: Colors.bgCard, borderRadius: Radius.md,
    padding: 16, marginTop: 12, border: `1px solid ${Colors.border}`,
  },
  hint: { fontSize: 11, color: Colors.textMuted, margin: '8px 0 0' },
};
