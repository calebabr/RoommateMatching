import { useState } from 'react';
import { useAdmin } from '../context/AuthContext';

export default function LoginPage() {
  const { login } = useAdmin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      const msg = err.message || err.response?.data?.detail || 'Login failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f5f5f5',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: 10,
        padding: '40px 48px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        width: 360,
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <span style={{ fontSize: 36 }}>🔒</span>
          <h1 style={{ margin: '12px 0 0', fontSize: 22, fontWeight: 700 }}>RoomMatch Admin</h1>
        </div>

        {error && (
          <div style={{
            background: '#fff0f0', border: '1px solid #dd4444',
            borderRadius: 6, padding: '10px 14px',
            color: '#dd4444', marginBottom: 20, fontSize: 14,
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 16 }}>
            <span style={{ fontSize: 13, color: '#555', display: 'block', marginBottom: 6 }}>Email</span>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{
                width: '100%', boxSizing: 'border-box',
                padding: '10px 12px', borderRadius: 6,
                border: '1px solid #e0e0e0', fontSize: 14,
              }}
            />
          </label>
          <label style={{ display: 'block', marginBottom: 24 }}>
            <span style={{ fontSize: 13, color: '#555', display: 'block', marginBottom: 6 }}>Password</span>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              style={{
                width: '100%', boxSizing: 'border-box',
                padding: '10px 12px', borderRadius: 6,
                border: '1px solid #e0e0e0', fontSize: 14,
              }}
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '11px',
              background: loading ? '#aaa' : '#0066cc',
              color: '#ffffff', border: 'none', borderRadius: 6,
              fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
