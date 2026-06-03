import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getNotifications, markNotificationsRead } from '../services/api';
import Spinner from '../components/Spinner';

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 60000);
  if (diff < 1)  return 'just now';
  if (diff < 60) return `${diff}m ago`;
  const h = Math.floor(diff / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

const NOTIF_ICON  = { like_received: '💌', match_created: '🎉', unmatch: '💔' };
const NOTIF_COLOR = { like_received: '#F87171', match_created: '#4ADE80', unmatch: '#666666' };

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      if (!user?.id) return;
      try {
        const data = await getNotifications(user.id);
        if (active) setNotifications(data);
        await markNotificationsRead(user.id);
      } catch {
        if (active) setNotifications([]);
      }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [user?.id]);

  if (loading) return (
    <div className="full-height flex-center bg-base">
      <Spinner size={40} />
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      <div className="page-container">
        {/* Header */}
        <div className="page-header">
          <button className="notifications-back-btn" onClick={() => navigate(-1)}>← Back</button>
          <span className="notifications-header-title">Activity</span>
          <div className="notifications-header-spacer" />
        </div>

        {notifications.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize: 56 }}>🔔</span>
            <p className="empty-state-title">No Activity Yet</p>
            <p className="empty-state-desc">Likes, matches, and updates will appear here.</p>
          </div>
        ) : (
          <div className="notifications-list">
            {notifications.map(item => {
              const icon  = NOTIF_ICON[item.type]  || '🔔';
              const color = NOTIF_COLOR[item.type] || 'var(--color-accent)';
              const clickable = item.type === 'like_received' || item.type === 'match_created';
              return (
                <div
                  key={item.id}
                  className={`notifications-item ${item.read ? 'notifications-item--read' : 'notifications-item--unread'} ${clickable ? 'notifications-item--clickable' : 'notifications-item--static'}`}
                  onClick={() => clickable && navigate(`/user/${item.fromUser}`)}
                >
                  <div
                    className="notifications-icon-circle"
                    style={{ backgroundColor: color + '20', border: `1.5px solid ${color}` }}
                  >
                    <span className="notifications-icon-emoji">{icon}</span>
                  </div>
                  <div className="notifications-content">
                    <p className="notifications-message">{item.message}</p>
                    <p className="notifications-time">{timeAgo(item.createdAt)}</p>
                  </div>
                  {!item.read && (
                    <div
                      className="notifications-unread-dot"
                      style={{ backgroundColor: color }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
