import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors } from '../utils/theme';
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

  if (loading) return (
    <div className="loading-page">
      <Spinner size={40} />
      <p className="text-secondary" style={{ fontSize: 14, margin: 0 }}>Loading likes...</p>
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      <div className="page-container">
        <div className="page-header">
          <div>
            <p className="page-header-title">Likes</p>
            <p className="page-header-sub">{likes.length} {likes.length === 1 ? 'person likes' : 'people like'} you</p>
          </div>
          <NotificationBell />
        </div>

        {likes.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize: 56 }}>💌</span>
            <p className="empty-state-title">No Likes Yet</p>
            <p className="empty-state-desc">When someone likes you, they'll appear here.</p>
          </div>
        ) : (
          <div className="likes-grid">
            {likes.map((item, i) => {
              const p = item.profile;
              const photoSrc = getPhotoUrl(p?.photoUrl);
              return (
                <div key={`${item.fromUser}-${i}`} className="likes-card">
                  <div className="likes-user-row" onClick={() => navigate(`/user/${p.id}`)}>
                    {photoSrc ? (
                      <img src={photoSrc} alt="" className="likes-avatar-img" />
                    ) : (
                      <div className="likes-avatar">
                        <span className="avatar-letter-danger">{(p.username || '?')[0].toUpperCase()}</span>
                      </div>
                    )}
                    <div style={{ flex: 1 }}>
                      <p className="likes-username">{p.username || `User #${p.id}`}</p>
                      <p className="likes-tagline">Wants to be your roommate!</p>
                    </div>
                  </div>
                  <div className="likes-actions">
                    <button className="likes-like-back-btn" onClick={() => handleLikeBack(p.id)} disabled={actionId === p.id}>
                      {actionId === p.id ? <Spinner size={16} color={Colors.black} /> : '♥ Like Back'}
                    </button>
                    <button className="likes-view-btn" onClick={() => navigate(`/user/${p.id}`)}>View Profile</button>
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
