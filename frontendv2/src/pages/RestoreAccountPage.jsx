import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Colors } from '../utils/theme';
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
    <div className="restore-page">
      <div className="restore-card">
        <p className="restore-title">Restore Account</p>

        {success ? (
          <>
            <p className="restore-success-msg">
              Account restored! You can now log in.
            </p>
            <Link to="/login" className="restore-login-link">Go to Login</Link>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="restore-label">Restore Token</label>
            <input
              type="text"
              className="restore-input"
              value={token}
              onChange={e => { setToken(e.target.value); setError(''); }}
              placeholder="Paste your restore token here"
              autoFocus
            />

            {error && (
              <p className="restore-error">{error}</p>
            )}

            <button
              type="submit"
              className={`restore-submit-btn ${(!token.trim() || loading) ? 'restore-submit-btn--disabled' : ''}`}
              disabled={!token.trim() || loading}
            >
              {loading ? <Spinner size={18} color={Colors.black} /> : 'Restore Account'}
            </button>

            <p className="restore-footer">
              Remember your password?{' '}
              <Link to="/login" className="restore-inline-login-link">Log in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
