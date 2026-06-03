import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { restoreAccount } from '../services/api';
import Spinner from '../components/Spinner';

export default function RestoreAccountPage() {
  const [token,     setToken]     = useState('');
  const [loading,   setLoading]   = useState(false);
  const [success,   setSuccess]   = useState(false);
  const [error,     setError]     = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token.trim()) return;
    setLoading(true);
    setError('');
    try {
      await restoreAccount(token.trim());
      setSuccess(true);
    } catch {
      setError('Invalid or expired token.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.page}>
      <div style={S.card}>
        <p style={S.title}>Restore Account</p>

        {success ? (
          <>
            <p style={{ fontSize: 15, color: Colors.success, margin: '0 0 20px', lineHeight: '22px' }}>
              Account restored! You can now log in.
            </p>
            <Link to="/login" style={S.loginLink}>Go to Login</Link>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <label style={S.label}>Restore Token</label>
            <input
              type="text"
              style={S.input}
              value={token}
              onChange={e => { setToken(e.target.value); setError(''); }}
              placeholder="Paste your restore token here"
              autoFocus
            />

            {error && (
              <p style={{ fontSize: 13, color: Colors.danger, margin: '8px 0 0', lineHeight: '18px' }}>{error}</p>
            )}

            <button
              type="submit"
              style={{ ...S.submitBtn, opacity: (!token.trim() || loading) ? 0.6 : 1 }}
              disabled={!token.trim() || loading}
            >
              {loading ? <Spinner size={18} color={Colors.black} /> : 'Restore Account'}
            </button>

            <p style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: Colors.textMuted }}>
              Remember your password?{' '}
              <Link to="/login" style={{ color: Colors.accent, fontWeight: 600, textDecoration: 'none' }}>Log in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

const S = {
  page:      { minHeight: '100dvh', backgroundColor: Colors.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 },
  card:      { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 32, width: '100%', maxWidth: 420, border: `1px solid ${Colors.border}` },
  title:     { fontSize: 22, fontWeight: 800, color: Colors.textPrimary, margin: '0 0 20px', textAlign: 'center' },
  label:     { display: 'block', fontSize: 12, fontWeight: 600, color: Colors.textSecondary, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.8 },
  input:     { width: '100%', backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '13px 16px', fontSize: 15, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none', boxSizing: 'border-box' },
  submitBtn: { width: '100%', marginTop: 16, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '14px 0', fontSize: 16, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  loginLink: { display: 'block', textAlign: 'center', padding: '12px 0', backgroundColor: Colors.accentGlow, borderRadius: Radius.md, border: `1px solid ${Colors.accent}`, fontSize: 15, fontWeight: 600, color: Colors.accent, textDecoration: 'none' },
};
