import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Colors } from '../utils/theme';
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
    <div className="auth-page">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}
      <div className="auth-scroll">
        <div className="auth-brand">
          <span style={{ fontSize: 52 }}>🏠</span>
          <h1 className="auth-brand-title">RoomMatch</h1>
          <p className="auth-brand-subtitle">Find your perfect roommate</p>
        </div>

        <form className="auth-card" onSubmit={handleLogin}>
          <p className="auth-card-title">Welcome Back</p>
          <p className="auth-card-desc">Sign in to your account</p>

          <div className="input-group">
            <label className="form-label">Email</label>
            <input
              className="form-input"
              placeholder="you@example.com"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoFocus
            />
          </div>

          <div className="input-group">
            <label className="form-label">Password</label>
            <div className="login-input-wrapper">
              <input
                className="form-input login-input-padded"
                placeholder="Enter your password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword(p => !p)}
                className="password-toggle-btn"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className={`btn-primary${loading ? ' btn-disabled' : ''}`}
            style={{ marginBottom: 4 }}
            disabled={loading}
          >
            {loading ? <Spinner size={20} color={Colors.black} /> : 'Sign In'}
          </button>

          <div className="login-forgot-row">
            <Link to="/forgot-password" className="login-forgot-link">Forgot password?</Link>
          </div>

          <div className="login-divider">
            <div className="login-divider-line" />
            <span className="login-divider-text">OR</span>
            <div className="login-divider-line" />
          </div>

          <button type="button" className="btn-secondary" onClick={() => navigate('/signup')}>
            Create Account
          </button>
        </form>

        {import.meta.env.DEV && (
          <>
            <button className="login-server-toggle" onClick={() => setShowServer(s => !s)}>
              {showServer ? '▼' : '▸'} Server Settings
            </button>

            {showServer && (
              <div className="login-server-card">
                <label className="form-label">Backend URL</label>
                <input
                  className="form-input"
                  placeholder="http://192.168.x.x:8000/api"
                  value={serverUrl}
                  onChange={e => { setServerUrl(e.target.value); setApiBase(e.target.value); }}
                />
                <p className="login-server-hint">Use your machine's local IP when testing on a physical device</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
