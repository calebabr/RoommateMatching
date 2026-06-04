import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUnreadNotificationCount, submitFeedback } from '../services/api';

function FeedbackModal({ onClose }) {
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState(null);
  const MAX = 2000;
  const handleSubmit = async () => {
    if (!message.trim()) return;
    try {
      await submitFeedback(message.trim());
      setStatus('success');
      setTimeout(onClose, 1500);
    } catch {
      setStatus('error');
    }
  };
  return (
    <div className="modal-overlay" style={{ zIndex: 10000 }}>
      <div className="modal-box" style={{ maxWidth: 480, width: '90%' }}>
        <p className="modal-title">Send Feedback</p>
        {status === 'success' ? (
          <p style={{ color: 'var(--color-success, #22aa55)', fontSize: 15, textAlign: 'center', padding: '8px 0' }}>Thanks for your feedback!</p>
        ) : (
          <>
            <textarea
              className="modal-textarea"
              placeholder="Describe the bug or share a suggestion..."
              value={message}
              onChange={e => setMessage(e.target.value.slice(0, MAX))}
              rows={5}
              style={{ width: '100%', resize: 'vertical', marginBottom: 4 }}
            />
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', textAlign: 'right', marginBottom: 12 }}>{message.length}/{MAX}</p>
            {status === 'error' && <p style={{ color: '#e55', fontSize: 13, marginBottom: 8 }}>Something went wrong. Please try again.</p>}
            <div className="modal-actions">
              <button className="modal-btn modal-btn--cancel" onClick={onClose}>Cancel</button>
              <button className="modal-btn modal-btn--confirm" onClick={handleSubmit} disabled={!message.trim()}>Submit</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function NotificationBell() {
  const navigate = useNavigate();
  const { user }  = useAuth();
  const [count, setCount] = useState(0);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const timerRef = useRef(null);

  const fetchCount = async () => {
    if (!user?.id) return;
    try {
      const data = await getUnreadNotificationCount(user.id);
      setCount(data.count || 0);
    } catch {}
  };

  useEffect(() => {
    fetchCount();
    timerRef.current = setInterval(fetchCount, 5000);
    return () => clearInterval(timerRef.current);
  }, [user?.id]);

  const linkStyle = {
    fontSize: 11,
    color: 'rgba(255,255,255,0.4)',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '2px 4px',
    textDecoration: 'none',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <button style={linkStyle} onClick={() => setFeedbackOpen(true)}>Feedback</button>
      <a href="/terms" target="_blank" rel="noopener noreferrer" style={linkStyle}>Terms</a>
      <a href="/privacy" target="_blank" rel="noopener noreferrer" style={linkStyle}>Privacy</a>
      <button className="notif-bell-btn" onClick={() => navigate('/notifications')}>
        <span className="notif-bell-icon">🔔</span>
        {count > 0 && <span className="notif-bell-badge">{count > 99 ? '99+' : count}</span>}
      </button>
      {feedbackOpen && <FeedbackModal onClose={() => setFeedbackOpen(false)} />}
    </div>
  );
}
