import { useState, useEffect } from 'react';
import { adminGetFeedback } from '../services/adminApi';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

export default function FeedbackPage() {
  const [items,   setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  useEffect(() => {
    adminGetFeedback()
      .then(res => setItems(res.data?.feedback ?? res.data ?? []))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load feedback.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 24 }}>User Feedback</h2>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#888' }}>
          <div style={{
            width: 20, height: 20,
            border: '3px solid #e0e0e0',
            borderTopColor: '#0f3460',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          Loading feedback...
        </div>
      )}

      {!loading && error && (
        <p style={{ color: '#dd4444' }}>{error}</p>
      )}

      {!loading && !error && (
        <div style={{
          background: '#ffffff',
          borderRadius: 8,
          border: '1px solid #e0e0e0',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                {['User', 'Message', 'Submitted'].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px',
                    textAlign: 'left',
                    fontWeight: 600,
                    color: '#555',
                    borderBottom: '1px solid #e0e0e0',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ padding: '32px 16px', textAlign: 'center', color: '#aaa' }}>
                    No feedback submitted yet
                  </td>
                </tr>
              ) : items.map((item, i) => (
                <tr
                  key={item.id || i}
                  style={{
                    background: i % 2 === 0 ? '#ffffff' : '#fafafa',
                    borderBottom: '1px solid #f0f0f0',
                    verticalAlign: 'top',
                  }}
                >
                  <td style={{ padding: '12px 16px', fontWeight: 500, whiteSpace: 'nowrap' }}>
                    {item.username || item.user || item.email || '—'}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#333', lineHeight: 1.6, wordBreak: 'break-word' }}>
                    {item.message}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#555', fontSize: 13, whiteSpace: 'nowrap' }}>
                    {formatDate(item.createdAt || item.submitted_at || item.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
