import { useState, useEffect, useCallback } from 'react';
import {
  adminGetConversationReports,
  adminGetReportMessages,
  adminResolveConversationReport,
} from '../services/adminApi';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function MessageThread({ reportId }) {
  const [messages, setMessages] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');

  useEffect(() => {
    adminGetReportMessages(reportId)
      .then(res => setMessages(res.data?.messages ?? res.data ?? []))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load messages.'))
      .finally(() => setLoading(false));
  }, [reportId]);

  if (loading) return <p style={{ color: '#888', fontSize: 13, padding: '8px 0' }}>Loading messages...</p>;
  if (error)   return <p style={{ color: '#dd4444', fontSize: 13 }}>{error}</p>;
  if (messages.length === 0) return <p style={{ color: '#aaa', fontSize: 13 }}>No messages found.</p>;

  return (
    <div style={{
      maxHeight: 300,
      overflowY: 'auto',
      border: '1px solid #e0e0e0',
      borderRadius: 6,
      background: '#fafafa',
      padding: '8px 0',
    }}>
      {messages.map((msg, i) => (
        <div key={msg.id || i} style={{
          padding: '8px 14px',
          borderBottom: i < messages.length - 1 ? '1px solid #f0f0f0' : 'none',
        }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', marginBottom: 3 }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: '#0f3460' }}>
              {msg.sender_name || msg.sender || msg.from || 'Unknown'}
            </span>
            <span style={{ fontSize: 12, color: '#aaa' }}>
              {formatDate(msg.createdAt || msg.timestamp || msg.sent_at)}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: '#333', lineHeight: 1.5, wordBreak: 'break-word' }}>
            {msg.content || msg.message || msg.text || ''}
          </p>
        </div>
      ))}
    </div>
  );
}

function ReportRow({ report, onResolved }) {
  const [expanded,    setExpanded]    = useState(false);
  const [confirming,  setConfirming]  = useState(false); // 'ban' | false
  const [acting,      setActing]      = useState(false);
  const [actionError, setActionError] = useState('');

  const handleAction = useCallback(async (action) => {
    setActing(true);
    setActionError('');
    try {
      await adminResolveConversationReport(report.id || report._id, action);
      onResolved(report.id || report._id);
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Action failed. Please try again.');
    } finally {
      setActing(false);
      setConfirming(false);
    }
  }, [report, onResolved]);

  return (
    <>
      <tr
        onClick={() => setExpanded(e => !e)}
        style={{ cursor: 'pointer', background: expanded ? '#f0f6ff' : undefined, borderBottom: '1px solid #f0f0f0' }}
        onMouseEnter={e => { if (!expanded) e.currentTarget.style.background = '#f5f5f5'; }}
        onMouseLeave={e => { if (!expanded) e.currentTarget.style.background = ''; }}
      >
        <td style={{ padding: '12px 16px', fontWeight: 500 }}>
          {report.reporter_name || report.reporter || '—'}
        </td>
        <td style={{ padding: '12px 16px' }}>
          {report.reported_name || report.reported_user || '—'}
        </td>
        <td style={{ padding: '12px 16px', color: '#555' }}>
          {report.reason || '—'}
        </td>
        <td style={{ padding: '12px 16px', color: '#555', fontSize: 13 }}>
          {formatDate(report.createdAt || report.created_at || report.timestamp)}
        </td>
        <td style={{ padding: '12px 16px', color: '#888', fontSize: 12 }}>
          {expanded ? '▲ Hide' : '▼ View'}
        </td>
      </tr>

      {expanded && (
        <tr style={{ background: '#f8faff' }}>
          <td colSpan={5} style={{ padding: '16px 24px', borderBottom: '1px solid #e0e0e0' }}>

            <h4 style={{ margin: '0 0 10px', fontSize: 14, color: '#333' }}>Message History</h4>
            <MessageThread reportId={report.id || report._id} />

            <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
              {confirming === 'ban' ? (
                <>
                  <span style={{ fontSize: 13, color: '#aa2200', fontWeight: 500 }}>
                    Ban the reported user? This cannot be undone easily.
                  </span>
                  <button
                    onClick={() => handleAction('ban')}
                    disabled={acting}
                    style={{
                      padding: '7px 16px', borderRadius: 6, border: 'none',
                      background: '#dd2222', color: '#fff', cursor: 'pointer',
                      fontSize: 13, fontWeight: 600,
                    }}
                  >
                    {acting ? 'Banning…' : 'Confirm Ban'}
                  </button>
                  <button
                    onClick={() => setConfirming(false)}
                    disabled={acting}
                    style={{
                      padding: '7px 16px', borderRadius: 6, border: '1px solid #ccc',
                      background: '#fff', color: '#333', cursor: 'pointer',
                      fontSize: 13,
                    }}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => handleAction('dismiss')}
                    disabled={acting}
                    style={{
                      padding: '7px 16px', borderRadius: 6, border: '1px solid #ccc',
                      background: '#fff', color: '#333', cursor: 'pointer',
                      fontSize: 13, fontWeight: 500,
                    }}
                  >
                    {acting ? 'Dismissing…' : 'Dismiss'}
                  </button>
                  <button
                    onClick={() => setConfirming('ban')}
                    disabled={acting}
                    style={{
                      padding: '7px 16px', borderRadius: 6, border: 'none',
                      background: '#dd2222', color: '#fff', cursor: 'pointer',
                      fontSize: 13, fontWeight: 600,
                    }}
                  >
                    Ban User
                  </button>
                </>
              )}
            </div>

            {actionError && (
              <p style={{ color: '#dd4444', fontSize: 13, marginTop: 8 }}>{actionError}</p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  useEffect(() => {
    adminGetConversationReports()
      .then(res => setReports(res.data?.reports ?? res.data ?? []))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load reports.'))
      .finally(() => setLoading(false));
  }, []);

  const handleResolved = useCallback((reportId) => {
    setReports(prev => prev.filter(r => (r.id || r._id) !== reportId));
  }, []);

  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 24 }}>Conversation Reports</h2>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: '#888' }}>
          <div style={{
            width: 20, height: 20,
            border: '3px solid #e0e0e0',
            borderTopColor: '#0f3460',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          Loading reports...
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
                {['Reporter', 'Reported User', 'Reason', 'Date', ''].map((h, i) => (
                  <th key={i} style={{
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
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '32px 16px', textAlign: 'center', color: '#aaa' }}>
                    No pending reports
                  </td>
                </tr>
              ) : reports.map((report) => (
                <ReportRow
                  key={report.id || report._id}
                  report={report}
                  onResolved={handleResolved}
                />
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
