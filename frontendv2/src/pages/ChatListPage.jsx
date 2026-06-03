import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
    <div className="loading-page">
      <Spinner size={40} />
      <p className="text-secondary" style={{ fontSize: 14, margin: 0 }}>Loading conversations...</p>
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      <div className="page-container">
        <div className="page-header">
          <div>
            <p className="page-header-title">Chat</p>
            <p className="page-header-sub">{conversations.length} {conversations.length === 1 ? 'conversation' : 'conversations'}</p>
          </div>
          <NotificationBell />
        </div>

        {conversations.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize: 56 }}>💬</span>
            <p className="empty-state-title">No Chats Yet</p>
            <p className="empty-state-desc">Match with someone to start chatting!</p>
          </div>
        ) : (
          <div className="chatlist-list">
            {conversations.map(item => {
              const p = item.profile;
              const photoSrc = getPhotoUrl(p?.photoUrl);
              const lastMsg = item.lastMessage;
              return (
                <div key={item.partnerId} className="chatlist-card" onClick={() => navigate(`/chat/${p.id}`, { state: { partnerName: p.username } })}>
                  {photoSrc ? (
                    <img src={photoSrc} alt="" className="chatlist-avatar" />
                  ) : (
                    <div className="chatlist-avatar-fallback">
                      <span className="avatar-letter-success">{(p?.username || '?')[0].toUpperCase()}</span>
                    </div>
                  )}
                  <div className="chatlist-info">
                    <div className="chatlist-info-row">
                      <span className="chatlist-username">{p?.username || `User #${p?.id}`}</span>
                      {lastMsg && <span className="chatlist-time">{timeAgo(lastMsg.createdAt)}</span>}
                    </div>
                    <p className="chatlist-preview">
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
