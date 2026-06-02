import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
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
    <div style={S.page}>
      <div style={S.scroll}>
        <div style={S.brand}>
          <span style={{ fontSize: 52 }}>🏠</span>
          <h1 style={S.title}>RoomMatch</h1>
        </div>

        <form style={S.card} onSubmit={handleSubmit}>
          <p style={S.cardTitle}>Forgot Password</p>
          <p style={S.cardDesc}>Enter your email to get a reset token.</p>

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

          {error && <p style={S.error}>{error}</p>}

          {resetToken && (
            <div style={S.tokenBox}>
              <p style={S.tokenLabel}>Your reset token (copy this):</p>
              <code style={S.tokenCode}>{resetToken}</code>
              <p style={S.tokenNote}>In the future this will be sent to your email automatically.</p>
            </div>
          )}

          <button type="submit" style={{ ...S.button, ...(loading ? S.buttonDisabled : {}) }} disabled={loading}>
            {loading ? 'Sending...' : 'Get Reset Token'}
          </button>
        </form>

        <div style={S.footer}>
          <Link to="/login" style={S.link}>Back to login</Link>
        </div>
      </div>
    </div>
  );
}

const S = {
  page:   { height: '100dvh', backgroundColor: Colors.bg, overflowY: 'auto' },
  scroll: { maxWidth: 480, margin: '0 auto', padding: '0 24px 40px' },
  brand:  { textAlign: 'center', paddingTop: 60, marginBottom: 36 },
  title:  { fontSize: 34, fontWeight: 800, color: Colors.accent, letterSpacing: 1, margin: '12px 0 6px' },
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
    boxSizing: 'border-box',
  },
  button: {
    width: '100%', backgroundColor: Colors.accent,
    borderRadius: Radius.md, padding: '16px 0',
    fontSize: 16, fontWeight: 700, color: Colors.black,
    border: 'none', marginTop: 4, cursor: 'pointer',
  },
  buttonDisabled: { opacity: 0.6 },
  error: { fontSize: 14, color: '#e05252', margin: '0 0 16px' },
  tokenBox: {
    backgroundColor: Colors.bg, borderRadius: Radius.md,
    border: `1px solid ${Colors.border}`, padding: 16, marginBottom: 16,
  },
  tokenLabel: { fontSize: 13, fontWeight: 600, color: Colors.textSecondary, margin: '0 0 8px' },
  tokenCode: {
    display: 'block', fontFamily: 'monospace', fontSize: 13,
    color: Colors.accent, wordBreak: 'break-all',
    backgroundColor: Colors.bgInput, padding: '10px 12px',
    borderRadius: Radius.sm, margin: '0 0 10px',
  },
  tokenNote: { fontSize: 12, color: Colors.textMuted, margin: 0 },
  footer: { textAlign: 'center', marginTop: 24 },
  link: { fontSize: 13, color: Colors.accent, textDecoration: 'none' },
};
