import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Colors } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import posthog from 'posthog-js';
import { getChatMessages, sendChatMessage, getUser, getPhotoUrl, unmatchUser, markChatRead } from '../services/api';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

function formatMessageTime(dateStr) {
  if (!dateStr) return '';
  const utc = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
  const diff = Math.floor((Date.now() - new Date(utc)) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  const h = Math.floor(diff / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function formatSeenTime(dateStr, _tick) {
  if (!dateStr) return '';
  const utc = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
  const diff = Math.floor((Date.now() - new Date(utc)) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return `${diff}m ago`;
  const h = Math.floor(diff / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function ChatPage() {
  const navigate = useNavigate();
  const { partnerId } = useParams();
  const { state } = useLocation();
  const [headerHovered, setHeaderHovered] = useState(false);
  const { user, refreshUser } = useAuth();
  const [messages,          setMessages]          = useState([]);
  const [partnerLastReadAt, setPartnerLastReadAt] = useState(null);
  const [tick,              setTick]              = useState(0);
  const [newMsgDividerAt,   setNewMsgDividerAt]   = useState(null);
  const [partner,  setPartner]  = useState(state?.partnerName ? { id: parseInt(partnerId), username: state.partnerName } : null);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(true);
  const [sending,  setSending]  = useState(false);
  const [modal,    setModal]    = useState(null);
  const bottomRef      = useRef(null);
  const pollRef        = useRef(null);
  const myLastReadRef  = useRef(null);
  const initialLoadRef = useRef(true);
  const partnerIdNum = parseInt(partnerId, 10);

  const loadMessages = async (isInit = false) => {
    if (!user?.id || !partnerIdNum) return;
    try {
      const data = await getChatMessages(user.id, partnerIdNum);
      // Backend now returns { messages: [...], partner_last_read_at: string|null }
      // Fallback: if it's still a plain array (legacy), handle gracefully
      const msgs = Array.isArray(data) ? data : (data.messages || []);
      const pLastRead = Array.isArray(data) ? null : (data.partner_last_read_at || null);
      setMessages(msgs);
      setPartnerLastReadAt(pLastRead);
      if (isInit) {
        // Determine "new messages" divider: first partner message after my last read
        const myLastRead = myLastReadRef.current;
        if (myLastRead) {
          const firstNew = msgs.find(
            m => m.fromUser !== user.id && m.createdAt && m.createdAt > myLastRead
          );
          if (firstNew) setNewMsgDividerAt(firstNew.id);
        }
      }
    } catch {}
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try { const p = await getUser(partnerIdNum); if (active) setPartner(p); } catch {}
      // Snapshot "now" before marking as read, so we can compute new-msg divider
      myLastReadRef.current = new Date().toISOString();
      // Mark as read on open
      markChatRead(user.id, partnerIdNum).catch(() => {});
      await loadMessages(true);
      initialLoadRef.current = false;
      if (active) setLoading(false);
    })();
    pollRef.current = setInterval(async () => {
      if (!active) return;
      await loadMessages(false);
      // Mark as read again whenever new messages arrive from partner
      markChatRead(user.id, partnerIdNum).catch(() => {});
    }, 3000);
    return () => { active = false; clearInterval(pollRef.current); };
  }, [user?.id, partnerIdNum]);

  // Tick every 30s to force re-render of relative time strings (e.g. "just now" → "1m ago")
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setSending(true);
    setInput('');
    try {
      await sendChatMessage(user.id, partnerIdNum, text);
      posthog.capture('message_sent');
      await loadMessages();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send message.' });
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleUnmatch = () => {
    setModal({
      title: 'Unmatch',
      message: `Are you sure you want to unmatch with ${partner?.username || 'this user'}? You'll both return to the matching pool.`,
      danger: true,
      confirmText: 'Unmatch',
      onConfirm: async () => {
        try { await unmatchUser(user.id, partnerIdNum); await refreshUser(); navigate(-1); }
        catch (err) { setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not unmatch.' }); }
      },
    });
  };

  const partnerPhoto = getPhotoUrl(partner?.photoUrl);

  return (
    <div className="chat-page">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}

      {/* Header */}
      <div className="chat-header">
        <button className="chat-back-btn" onClick={() => navigate(-1)}>←</button>
        <div
          className="chat-partner-info"
          onClick={() => navigate(`/user/${partnerIdNum}`)}
          onMouseEnter={() => setHeaderHovered(true)}
          onMouseLeave={() => setHeaderHovered(false)}
          style={{ cursor: 'pointer', opacity: headerHovered ? 0.85 : 1, transition: 'opacity 0.15s ease' }}
        >
          {partnerPhoto ? (
            <img src={partnerPhoto} alt="" className="chat-partner-avatar-img" />
          ) : (
            <div className="chat-partner-avatar">
              <span className="avatar-letter-success" style={{ fontSize: 16 }}>{(partner?.username || '?')[0].toUpperCase()}</span>
            </div>
          )}
          <div>
            <p className="chat-partner-name">{partner?.username || 'Roommate'}</p>
            <p className="chat-partner-status">Matched roommate</p>
          </div>
        </div>
        <button className="chat-unmatch-btn" onClick={handleUnmatch}>Unmatch</button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {loading ? (
          <div className="chat-loading"><Spinner size={32} /></div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            <span style={{ fontSize: 48 }}>👋</span>
            <p className="chat-empty-title">Say hello!</p>
            <p className="chat-empty-desc">Start the conversation with your new roommate.</p>
          </div>
        ) : (() => {
          // Find last message sent by me
          const myMessages = messages.filter(m => m.fromUser === user.id);
          const lastSentMsg = myMessages.length > 0 ? myMessages[myMessages.length - 1] : null;
          // "Seen" receipt: partner has read past my last sent message
          const showSeen = lastSentMsg && partnerLastReadAt && lastSentMsg.createdAt <= partnerLastReadAt;

          return messages.map((msg) => {
            const isMe = msg.fromUser === user.id;
            const isLastSent = isMe && lastSentMsg && msg.id === lastSentMsg.id;
            const showDivider = newMsgDividerAt && msg.id === newMsgDividerAt;
            return (
              <React.Fragment key={msg.id}>
                {showDivider && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    margin: '8px 0',
                    padding: '0 12px',
                  }}>
                    <div style={{ flex: 1, height: 1, background: 'var(--color-border, rgba(255,255,255,0.12))' }} />
                    <span style={{ fontSize: 11, color: 'var(--color-text-secondary, #A0A0A0)', whiteSpace: 'nowrap' }}>
                      New messages
                    </span>
                    <div style={{ flex: 1, height: 1, background: 'var(--color-border, rgba(255,255,255,0.12))' }} />
                  </div>
                )}
                <div className={`chat-message-row ${isMe ? 'chat-message-row--mine' : 'chat-message-row--theirs'}`}>
                  <div className={`chat-bubble ${isMe ? 'chat-bubble--mine' : 'chat-bubble--theirs'}`}>
                    <p className={`chat-bubble-text ${isMe ? 'chat-bubble-text--mine' : 'chat-bubble-text--theirs'}`}>{msg.content}</p>
                    <p className={`chat-bubble-time ${isMe ? 'chat-bubble-time--mine' : 'chat-bubble-time--theirs'}`}>{formatMessageTime(msg.createdAt)}</p>
                  </div>
                </div>
                {isLastSent && showSeen && (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '0 16px 4px', marginTop: -4 }}>
                    <span style={{ fontSize: 11, color: 'var(--color-text-secondary, #A0A0A0)' }}>
                      Seen {formatSeenTime(partnerLastReadAt, tick)}
                    </span>
                  </div>
                )}
              </React.Fragment>
            );
          });
        })()}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-bar">
        <textarea
          className="chat-input"
          placeholder="Type a message..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          maxLength={1000}
        />
        <button
          className={`chat-send-btn ${!input.trim() || sending ? 'chat-send-btn--disabled' : ''}`}
          onClick={handleSend}
          disabled={!input.trim() || sending}
        >
          {sending ? <Spinner size={18} color={Colors.black} /> : '↑'}
        </button>
      </div>
    </div>
  );
}
