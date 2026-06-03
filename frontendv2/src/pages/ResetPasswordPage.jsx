import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authResetPassword } from '../services/api';

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

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const params = new URLSearchParams(window.location.search);
  const tokenFromUrl = params.get('token') || '';

  const [token,       setToken]       = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [loading,     setLoading]     = useState(false);
  const [success,     setSuccess]     = useState(false);
  const [error,       setError]       = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!token.trim() || !newPassword) { setError('Please fill in both fields.'); return; }
    setLoading(true);
    try {
      await authResetPassword(token.trim(), newPassword);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Reset failed. The token may be invalid or expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-scroll">
        <div className="auth-brand">
          <span style={{ fontSize: 52 }}>🏠</span>
          <h1 className="auth-brand-title">RoomMatch</h1>
        </div>

        <form className="auth-card" onSubmit={handleSubmit}>
          <p className="auth-card-title">Reset Password</p>
          <p className="auth-card-desc">Enter your reset token and a new password.</p>

          <div className="input-group">
            <label className="form-label">Token</label>
            <input
              className="form-input"
              placeholder="Paste your reset token"
              type="text"
              value={token}
              onChange={e => setToken(e.target.value)}
              autoFocus={!tokenFromUrl}
            />
          </div>

          <div className="input-group">
            <label className="form-label">New Password</label>
            <div className="resetpw-input-wrapper">
              <input
                className="form-input login-input-padded"
                placeholder="Enter new password"
                type={showNewPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                autoFocus={!!tokenFromUrl}
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(p => !p)}
                className="password-toggle-btn"
                aria-label={showNewPassword ? 'Hide password' : 'Show password'}
              >
                {showNewPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          {error && <p className="resetpw-error">{error}</p>}
          {success && <p className="resetpw-success">Password reset successfully! Redirecting to login...</p>}

          <button
            type="submit"
            className={`resetpw-btn ${loading || success ? 'resetpw-btn--disabled' : ''}`}
            disabled={loading || success}
          >
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
}
