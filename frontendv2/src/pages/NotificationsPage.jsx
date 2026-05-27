import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
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
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.bg }}>
      <Spinner size={40} />
    </div>
  );

  return (
    <div style={{ height: '100%', overflowY: 'auto', backgroundColor: Colors.bg }}>
      <div style={S.page}>
        {/* Header */}
        <div style={S.header}>
          <button style={S.backBtn} onClick={() => navigate(-1)}>← Back</button>
          <span style={{ fontSize: 24, fontWeight: 800, color: Colors.textPrimary }}>Activity</span>
          <div style={{ width: 80 }} />
        </div>

        {notifications.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12 }}>
            <span style={{ fontSize: 56 }}>🔔</span>
            <p style={{ fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>No Activity Yet</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: '20px', margin: 0 }}>Likes, matches, and updates will appear here.</p>
          </div>
        ) : (
          <div style={S.list}>
            {notifications.map(item => {
              const icon  = NOTIF_ICON[item.type]  || '🔔';
              const color = NOTIF_COLOR[item.type] || Colors.accent;
              const clickable = item.type === 'like_received' || item.type === 'match_created';
              return (
                <div
                  key={item.id}
                  style={{
                    display: 'flex', alignItems: 'center',
                    backgroundColor: item.read ? Colors.bgCard : Colors.accentGlow,
                    borderRadius: Radius.md, padding: 16,
                    border: `1px solid ${item.read ? Colors.border : Colors.accent + '40'}`,
                    cursor: clickable ? 'pointer' : 'default',
                  }}
                  onClick={() => clickable && navigate(`/user/${item.fromUser}`)}
                >
                  <div style={{ width: 44, height: 44, borderRadius: '50%', backgroundColor: color + '20', border: `1.5px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14, flexShrink: 0 }}>
                    <span style={{ fontSize: 20 }}>{icon}</span>
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 14, fontWeight: 600, color: Colors.textPrimary, lineHeight: '20px', margin: '0 0 4px' }}>{item.message}</p>
                    <p style={{ fontSize: 12, color: Colors.textMuted, margin: 0 }}>{timeAgo(item.createdAt)}</p>
                  </div>
                  {!item.read && (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: color, marginLeft: 8, flexShrink: 0 }} />
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

const S = {
  page:    { padding: '28px 32px 40px' },
  header:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  backBtn: { background: 'none', border: 'none', fontSize: 15, color: Colors.accent, fontWeight: 600, cursor: 'pointer', padding: 0 },
  list:    { display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 800 },
};
