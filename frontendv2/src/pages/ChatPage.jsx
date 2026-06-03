import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Colors } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatMessages, sendChatMessage, getUser, getPhotoUrl, unmatchUser } from '../services/api';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

function formatTime(dateStr) {
  if (!dateStr) return '';
  const s = typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+') ? dateStr + 'Z' : dateStr;
  const d = new Date(s);
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${m} ${ampm}`;
}

export default function ChatPage() {
  const navigate = useNavigate();
  const { partnerId } = useParams();
  const { state } = useLocation();
  const { user, refreshUser } = useAuth();
  const [messages, setMessages] = useState([]);
  const [partner,  setPartner]  = useState(state?.partnerName ? { id: parseInt(partnerId), username: state.partnerName } : null);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(true);
  const [sending,  setSending]  = useState(false);
  const [modal,    setModal]    = useState(null);
  const bottomRef = useRef(null);
  const pollRef   = useRef(null);
  const partnerIdNum = parseInt(partnerId, 10);

  const loadMessages = async () => {
    if (!user?.id || !partnerIdNum) return;
    try { const msgs = await getChatMessages(user.id, partnerIdNum); setMessages(msgs); }
    catch {}
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try { const p = await getUser(partnerIdNum); if (active) setPartner(p); } catch {}
      await loadMessages();
      if (active) setLoading(false);
    })();
    pollRef.current = setInterval(() => { if (active) loadMessages(); }, 3000);
    return () => { active = false; clearInterval(pollRef.current); };
  }, [user?.id, partnerIdNum]);

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
        <div className="chat-partner-info">
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
        ) : (
          messages.map(msg => {
            const isMe = msg.fromUser === user.id;
            return (
              <div key={msg.id} className={`chat-message-row ${isMe ? 'chat-message-row--mine' : 'chat-message-row--theirs'}`}>
                <div className={`chat-bubble ${isMe ? 'chat-bubble--mine' : 'chat-bubble--theirs'}`}>
                  <p className={`chat-bubble-text ${isMe ? 'chat-bubble-text--mine' : 'chat-bubble-text--theirs'}`}>{msg.content}</p>
                  <p className={`chat-bubble-time ${isMe ? 'chat-bubble-time--mine' : 'chat-bubble-time--theirs'}`}>{formatTime(msg.createdAt)}</p>
                </div>
              </div>
            );
          })
        )}
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
