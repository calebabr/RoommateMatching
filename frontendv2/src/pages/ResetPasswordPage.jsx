import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { authResetPassword } from '../services/api';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const params = new URLSearchParams(window.location.search);
  const tokenFromUrl = params.get('token') || '';

  const [token,       setToken]       = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState('');
  const [loading,     setLoading]     = useState(false);
  const [success,     setSuccess]     = useState(false);
  const [error,       setError]       = useState('');

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
    <div style={S.page}>
      <div style={S.scroll}>
        <div style={S.brand}>
          <span style={{ fontSize: 52 }}>🏠</span>
          <h1 style={S.title}>RoomMatch</h1>
        </div>

        <form style={S.card} onSubmit={handleSubmit}>
          <p style={S.cardTitle}>Reset Password</p>
          <p style={S.cardDesc}>Enter your reset token and a new password.</p>

          <div style={S.inputGroup}>
            <label style={S.label}>Token</label>
            <input
              style={S.input}
              placeholder="Paste your reset token"
              type="text"
              value={token}
              onChange={e => setToken(e.target.value)}
              autoFocus={!tokenFromUrl}
            />
          </div>

          <div style={S.inputGroup}>
            <label style={S.label}>New Password</label>
            <input
              style={S.input}
              placeholder="Enter new password"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              autoFocus={!!tokenFromUrl}
            />
          </div>

          {error && <p style={S.error}>{error}</p>}
          {success && <p style={S.successMsg}>Password reset successfully! Redirecting to login...</p>}

          <button type="submit" style={{ ...S.button, ...(loading || success ? S.buttonDisabled : {}) }} disabled={loading || success}>
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
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
  error:      { fontSize: 14, color: '#e05252', margin: '0 0 16px' },
  successMsg: { fontSize: 14, color: '#4caf50', margin: '0 0 16px', fontWeight: 600 },
};
