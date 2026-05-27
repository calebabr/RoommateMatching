import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatConversations, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';
import Spinner from '../components/Spinner';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 60000);
  if (diff < 1)  return 'just now';
  if (diff < 60) return `${diff}m ago`;
  const h = Math.floor(diff / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function ChatListPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      await refreshUser();
      try {
        const convos = await getChatConversations(user.id);
        const enriched = await Promise.all(
          convos.map(async (c) => {
            try { const p = await getUser(c.partnerId); return { ...c, profile: p }; }
            catch { return { ...c, profile: { id: c.partnerId, username: `User #${c.partnerId}` } }; }
          })
        );
        if (active) setConversations(enriched);
      } catch { if (active) setConversations([]); }
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [user?.id]);

  if (loading) return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
      <Spinner size={40} />
      <p style={{ color: Colors.textSecondary, fontSize: 14, margin: 0 }}>Loading conversations...</p>
    </div>
  );

  return (
    <div style={{ height: '100%', overflowY: 'auto', backgroundColor: Colors.bg }}>
      <div style={S.page}>
        <div style={S.header}>
          <div>
            <p style={S.headerTitle}>Chat</p>
            <p style={S.headerSub}>{conversations.length} {conversations.length === 1 ? 'conversation' : 'conversations'}</p>
          </div>
          <NotificationBell />
        </div>

        {conversations.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12 }}>
            <span style={{ fontSize: 56 }}>💬</span>
            <p style={{ fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>No Chats Yet</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: '20px', margin: 0 }}>Match with someone to start chatting!</p>
          </div>
        ) : (
          <div style={S.list}>
            {conversations.map(item => {
              const p = item.profile;
              const photoSrc = getPhotoUrl(p?.photoUrl);
              const lastMsg = item.lastMessage;
              return (
                <div key={item.partnerId} style={S.card} onClick={() => navigate(`/chat/${p.id}`, { state: { partnerName: p.username } })}>
                  {photoSrc ? (
                    <img src={photoSrc} alt="" style={S.avatar} />
                  ) : (
                    <div style={S.avatarFallback}><span style={{ fontSize: 22, fontWeight: 800, color: Colors.success }}>{(p?.username || '?')[0].toUpperCase()}</span></div>
                  )}
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 16, fontWeight: 700, color: Colors.textPrimary }}>{p?.username || `User #${p?.id}`}</span>
                      {lastMsg && <span style={{ fontSize: 11, color: Colors.textMuted }}>{timeAgo(lastMsg.createdAt)}</span>}
                    </div>
                    <p style={{ fontSize: 13, color: Colors.textSecondary, margin: 0, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                      {lastMsg ? (lastMsg.fromUser === user.id ? `You: ${lastMsg.content}` : lastMsg.content) : 'No messages yet — say hello!'}
                    </p>
                  </div>
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
  page:         { padding: '28px 32px 40px' },
  header:       { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  headerTitle:  { fontSize: 24, fontWeight: 800, color: Colors.textPrimary, margin: 0 },
  headerSub:    { fontSize: 13, color: Colors.textSecondary, margin: '2px 0 0' },
  list:         { display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 800 },
  card:         { display: 'flex', alignItems: 'center', backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 16, border: `1px solid ${Colors.border}`, cursor: 'pointer' },
  avatar:       { width: 52, height: 52, borderRadius: '50%', objectFit: 'cover', marginRight: 14, border: `2px solid ${Colors.success}`, flexShrink: 0 },
  avatarFallback:{ width: 52, height: 52, borderRadius: '50%', backgroundColor: Colors.successDim, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14, border: `2px solid ${Colors.success}`, flexShrink: 0 },
};
