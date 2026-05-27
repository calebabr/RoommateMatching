import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatMessages, sendChatMessage, getUser, getPhotoUrl, unmatchUser } from '../services/api';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

function formatTime(dateStr) {
  const d = new Date(dateStr);
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
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: Colors.bg }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}

      {/* Header */}
      <div style={S.header}>
        <button style={S.backBtn} onClick={() => navigate(-1)}>←</button>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
          {partnerPhoto ? (
            <img src={partnerPhoto} alt="" style={S.partnerAvatarImg} />
          ) : (
            <div style={S.partnerAvatar}>
              <span style={{ fontSize: 16, fontWeight: 800, color: Colors.success }}>{(partner?.username || '?')[0].toUpperCase()}</span>
            </div>
          )}
          <div>
            <p style={{ fontSize: 16, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>{partner?.username || 'Roommate'}</p>
            <p style={{ fontSize: 11, color: Colors.success, margin: 0 }}>Matched roommate</p>
          </div>
        </div>
        <button style={S.unmatchBtn} onClick={handleUnmatch}>Unmatch</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px 8px' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 40 }}><Spinner size={32} /></div>
        ) : messages.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 8 }}>
            <span style={{ fontSize: 48 }}>👋</span>
            <p style={{ fontSize: 20, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>Say hello!</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center' }}>Start the conversation with your new roommate.</p>
          </div>
        ) : (
          messages.map(msg => {
            const isMe = msg.fromUser === user.id;
            return (
              <div key={msg.id} style={{ display: 'flex', justifyContent: isMe ? 'flex-end' : 'flex-start', marginBottom: 8 }}>
                <div style={{
                  maxWidth: '60%', padding: '10px 16px', borderRadius: 20,
                  borderBottomRightRadius: isMe ? 4 : 20,
                  borderBottomLeftRadius:  isMe ? 20 : 4,
                  backgroundColor: isMe ? Colors.accent : Colors.bgCard,
                  border: isMe ? 'none' : `1px solid ${Colors.border}`,
                }}>
                  <p style={{ fontSize: 15, lineHeight: '21px', color: isMe ? Colors.black : Colors.textPrimary, margin: '0 0 4px' }}>{msg.content}</p>
                  <p style={{ fontSize: 10, color: isMe ? 'rgba(0,0,0,0.45)' : Colors.textMuted, margin: 0, textAlign: isMe ? 'right' : 'left' }}>{formatTime(msg.createdAt)}</p>
                </div>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={S.inputBar}>
        <textarea
          style={S.chatInput}
          placeholder="Type a message..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          maxLength={1000}
        />
        <button style={{ ...S.sendBtn, ...(!input.trim() || sending ? S.sendBtnDisabled : {}) }} onClick={handleSend} disabled={!input.trim() || sending}>
          {sending ? <Spinner size={18} color={Colors.black} /> : '↑'}
        </button>
      </div>
    </div>
  );
}

const S = {
  header:        { display: 'flex', alignItems: 'center', padding: '12px 20px', backgroundColor: Colors.bgCard, borderBottom: `1px solid ${Colors.border}`, flexShrink: 0 },
  backBtn:       { background: 'none', border: 'none', fontSize: 22, color: Colors.accent, fontWeight: 700, cursor: 'pointer', paddingRight: 12 },
  partnerAvatar: { width: 38, height: 38, borderRadius: '50%', backgroundColor: Colors.successDim, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 10, border: `2px solid ${Colors.success}`, flexShrink: 0 },
  partnerAvatarImg: { width: 38, height: 38, borderRadius: '50%', objectFit: 'cover', marginRight: 10, border: `2px solid ${Colors.success}`, flexShrink: 0 },
  unmatchBtn:    { padding: '6px 12px', borderRadius: Radius.full, border: `1.5px solid ${Colors.danger}`, background: 'none', fontSize: 12, fontWeight: 600, color: Colors.danger, cursor: 'pointer' },
  inputBar:      { display: 'flex', alignItems: 'flex-end', gap: 10, padding: '12px 20px 16px', backgroundColor: Colors.bgCard, borderTop: `1px solid ${Colors.border}`, flexShrink: 0 },
  chatInput:     { flex: 1, backgroundColor: Colors.bgInput, borderRadius: 22, padding: '10px 18px', fontSize: 15, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none', resize: 'none', maxHeight: 120, lineHeight: '21px', fontFamily: 'inherit' },
  sendBtn:       { width: 42, height: 42, borderRadius: '50%', backgroundColor: Colors.accent, border: 'none', fontSize: 20, fontWeight: 800, color: Colors.black, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  sendBtnDisabled: { opacity: 0.4 },
};
