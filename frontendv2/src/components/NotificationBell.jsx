import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUnreadNotificationCount, submitFeedback } from '../services/api';
import LegalModal from './LegalModal';

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
        <p className="modal-title" style={{ color: 'var(--color-accent, #E8A838)', fontSize: 20, fontWeight: 700 }}>Send Feedback</p>
        {status === 'success' ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <span style={{ fontSize: 32 }}>&#10003;</span>
            <p style={{ color: 'var(--color-success, #22aa55)', fontSize: 15, marginTop: 8 }}>Thanks for your feedback!</p>
          </div>
        ) : (
          <>
            <textarea
              className="modal-textarea"
              placeholder="Describe the bug or share a suggestion..."
              value={message}
              onChange={e => setMessage(e.target.value.slice(0, MAX))}
              rows={5}
              style={{
                width: '100%',
                resize: 'vertical',
                marginBottom: 4,
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: 8,
                color: '#fff',
                padding: '10px 12px',
                fontSize: 14,
                boxSizing: 'border-box',
                outline: 'none',
              }}
              onFocus={e => { e.target.style.outline = '1px solid #E8A838'; }}
              onBlur={e => { e.target.style.outline = 'none'; }}
            />
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', textAlign: 'right', marginBottom: 12 }}>{message.length}/{MAX}</p>
            {status === 'error' && <p style={{ color: '#e55', fontSize: 13, marginBottom: 8 }}>Something went wrong. Please try again.</p>}
            <div className="modal-actions">
              <button
                onClick={onClose}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.2)',
                  borderRadius: 8,
                  color: '#fff',
                  padding: '8px 20px',
                  fontSize: 14,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!message.trim()}
                style={{
                  background: message.trim() ? '#E8A838' : 'rgba(232,168,56,0.35)',
                  border: 'none',
                  borderRadius: 8,
                  color: message.trim() ? '#1a1a1a' : 'rgba(26,26,26,0.5)',
                  padding: '8px 20px',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: message.trim() ? 'pointer' : 'not-allowed',
                }}
              >
                Submit
              </button>
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
  const [legalModal, setLegalModal] = useState(null); // 'terms' | 'privacy' | null
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
      <button style={linkStyle} onClick={() => setLegalModal('terms')}>Terms</button>
      <button style={linkStyle} onClick={() => setLegalModal('privacy')}>Privacy</button>
      <button className="notif-bell-btn" onClick={() => navigate('/notifications')}>
        <span className="notif-bell-icon">🔔</span>
        {count > 0 && <span className="notif-bell-badge">{count > 99 ? '99+' : count}</span>}
      </button>
      {feedbackOpen && <FeedbackModal onClose={() => setFeedbackOpen(false)} />}
      {legalModal && <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />}
    </div>
  );
}
