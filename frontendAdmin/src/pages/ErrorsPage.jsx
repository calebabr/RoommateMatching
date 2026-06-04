import { useState, useEffect } from 'react';
import { adminGetErrors } from '../services/adminApi';

const LEVEL_STYLES = {
  error:   { background: '#ffeaea', color: '#dd2222', border: '1px solid #dd2222' },
  warning: { background: '#fff7e6', color: '#cc7700', border: '1px solid #cc7700' },
  info:    { background: '#e8f0ff', color: '#2255cc', border: '1px solid #2255cc' },
};

function LevelPill({ level }) {
  const style = LEVEL_STYLES[level] || LEVEL_STYLES.info;
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'capitalize',
      ...style,
    }}>
      {level || 'info'}
    </span>
  );
}

function StatusPill({ status }) {
  const isResolved = status === 'resolved';
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: isResolved ? '#eafff0' : '#ffeaea',
      color: isResolved ? '#22aa55' : '#dd4444',
      border: `1px solid ${isResolved ? '#22aa55' : '#dd4444'}`,
      textTransform: 'capitalize',
    }}>
      {status || 'unresolved'}
    </span>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

export default function ErrorsPage() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminGetErrors()
      .then(res => setData(res.data))
      .catch(err => setData({ error: err.response?.data?.detail || 'Failed to load error data.' }))
      .finally(() => setLoading(false));
  }, []);

  const issues = data?.issues || [];

  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 24 }}>Error Logs</h2>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#888' }}>
          <div style={{
            width: 20, height: 20,
            border: '3px solid #e0e0e0',
            borderTopColor: '#0f3460',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          Loading errors...
        </div>
      )}

      {!loading && data?.error && (
        <div style={{
          background: '#fff7e6',
          border: '1px solid #cc7700',
          borderRadius: 8,
          padding: '14px 18px',
          color: '#884400',
          fontSize: 14,
          marginBottom: 20,
        }}>
          <strong>Warning:</strong> {data.error}
        </div>
      )}

      {!loading && !data?.error && (
        <div style={{
          background: '#ffffff',
          borderRadius: 8,
          border: '1px solid #e0e0e0',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                {['Title', 'Level', 'Status', 'First Seen', 'Last Seen', 'Times Seen'].map(h => (
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
              {issues.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '32px 16px', textAlign: 'center', color: '#aaa' }}>
                    No errors in the last 7 days
                  </td>
                </tr>
              ) : issues.map((issue, i) => (
                <tr
                  key={issue.id || i}
                  style={{
                    background: i % 2 === 0 ? '#ffffff' : '#fafafa',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f0f6ff'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#ffffff' : '#fafafa'}
                >
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>
                    {issue.permalink ? (
                      <a
                        href={issue.permalink}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#0f3460', textDecoration: 'underline' }}
                      >
                        {issue.title || '(no title)'}
                      </a>
                    ) : (
                      issue.title || '(no title)'
                    )}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <LevelPill level={issue.level} />
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <StatusPill status={issue.status} />
                  </td>
                  <td style={{ padding: '12px 16px', color: '#555', fontSize: 13 }}>
                    {formatDate(issue.firstSeen)}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#555', fontSize: 13 }}>
                    {formatDate(issue.lastSeen)}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#555', fontWeight: 500 }}>
                    {issue.count ?? '—'}
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
