import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authForgotPassword } from '../services/api';

export default function ForgotPasswordPage() {
  const [email,     setEmail]     = useState('');
  const [loading,   setLoading]   = useState(false);
  const [resetToken, setResetToken] = useState(null);
  const [error,     setError]     = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResetToken(null);
    if (!email.trim()) { setError('Please enter your email address.'); return; }
    setLoading(true);
    try {
      const data = await authForgotPassword(email.trim());
      if (data.reset_token) {
        setResetToken(data.reset_token);
      } else {
        setError(data.message || 'No account found with that email.');
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
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
          <p className="auth-card-title">Forgot Password</p>
          <p className="auth-card-desc">Enter your email to get a reset token.</p>

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

          {error && <p className="forgotpw-error">{error}</p>}

          {resetToken && (
            <div className="forgotpw-token-box">
              <p className="forgotpw-token-label">Your reset token (copy this):</p>
              <code className="forgotpw-token-code">{resetToken}</code>
              <p className="forgotpw-token-note">In the future this will be sent to your email automatically.</p>
            </div>
          )}

          <button
            type="submit"
            className={`forgotpw-btn ${loading ? 'forgotpw-btn--disabled' : ''}`}
            disabled={loading}
          >
            {loading ? 'Sending...' : 'Get Reset Token'}
          </button>
        </form>

        <div className="forgotpw-footer">
          <Link to="/login" className="forgotpw-back-link">Back to login</Link>
        </div>
      </div>
    </div>
  );
}
