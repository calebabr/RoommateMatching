import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getLikesReceived, sendLike, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function LikesPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [likes,     setLikes]     = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [actionId,  setActionId]  = useState(null);
  const [modal,     setModal]     = useState(null);

  const loadLikes = async () => {
    if (!user?.id) return;
    try {
      const raw = await getLikesReceived(user.id);
      const enriched = await Promise.all(
        raw.map(async (like) => {
          try { const p = await getUser(like.fromUser); return { ...like, profile: p }; }
          catch { return { ...like, profile: { id: like.fromUser, username: `User #${like.fromUser}` } }; }
        })
      );
      setLikes(enriched);
    } catch { setLikes([]); }
  };

  useEffect(() => {
    let active = true;
    (async () => { setLoading(true); await loadLikes(); if (active) setLoading(false); })();
    return () => { active = false; };
  }, [user?.id]);

  const handleLikeBack = async (fromUserId) => {
    setActionId(fromUserId);
    try {
      const result = await sendLike(user.id, fromUserId);
      if (result.status === 'matched') {
        setModal({ title: '🎉 Match!', message: `You and User #${fromUserId} are now roommate matches!` });
        await refreshUser();
      } else {
        setModal({ title: 'Liked!', message: 'Your like has been sent.' });
      }
      await loadLikes();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send like.' });
    } finally {
      setActionId(null);
    }
  };

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}><Spinner size={40} /></div>;

  return (
    <div style={{ backgroundColor: Colors.bg, minHeight: '100%' }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      <div style={S.header}>
        <div>
          <p style={S.headerTitle}>Likes</p>
          <p style={S.headerSub}>{likes.length} {likes.length === 1 ? 'person likes' : 'people like'} you</p>
        </div>
        <NotificationBell />
      </div>

      {likes.length === 0 ? (
        <div style={S.centered}>
          <span style={{ fontSize: 56 }}>💌</span>
          <p style={S.emptyTitle}>No Likes Yet</p>
          <p style={S.emptySub}>When someone likes you, they'll appear here.</p>
        </div>
      ) : (
        <div style={{ padding: '0 20px 30px' }}>
          {likes.map((item, i) => {
            const p = item.profile;
            const photoSrc = getPhotoUrl(p?.photoUrl);
            return (
              <div key={`${item.fromUser}-${i}`} style={S.card}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, cursor: 'pointer' }} onClick={() => navigate(`/user/${p.id}`)}>
                  {photoSrc ? (
                    <img src={photoSrc} alt="" style={S.avatarImg} />
                  ) : (
                    <div style={S.avatar}><span style={{ fontSize: 22, fontWeight: 800, color: Colors.danger }}>{(p.username || '?')[0].toUpperCase()}</span></div>
                  )}
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>{p.username || `User #${p.id}`}</p>
                    <p style={{ fontSize: 13, color: Colors.textSecondary, margin: '2px 0 0' }}>Wants to be your roommate!</p>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button style={S.likeBackBtn} onClick={() => handleLikeBack(p.id)} disabled={actionId === p.id}>
                    {actionId === p.id ? <Spinner size={16} color={Colors.black} /> : '♥ Like Back'}
                  </button>
                  <button style={S.viewBtn} onClick={() => navigate(`/user/${p.id}`)}>View Profile</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const S = {
  header:     { padding: '20px 24px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle:{ fontSize: 28, fontWeight: 800, color: Colors.textPrimary, margin: 0 },
  headerSub:  { fontSize: 13, color: Colors.textSecondary, margin: '2px 0 0' },
  card:       { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 20, marginTop: 16, border: `1px solid ${Colors.border}` },
  avatar:     { width: 52, height: 52, borderRadius: '50%', backgroundColor: Colors.dangerDim, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14, border: `2px solid ${Colors.danger}`, flexShrink: 0 },
  avatarImg:  { width: 52, height: 52, borderRadius: '50%', objectFit: 'cover', marginRight: 14, border: `2px solid ${Colors.danger}`, flexShrink: 0 },
  likeBackBtn:{ flex: 1, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  viewBtn:    { flex: 1, backgroundColor: 'transparent', border: `1.5px solid ${Colors.border}`, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 600, color: Colors.textSecondary, cursor: 'pointer' },
  centered:   { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40, minHeight: '60vh' },
  emptyTitle: { fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: '16px 0 8px' },
  emptySub:   { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: '20px', margin: 0 },
};
