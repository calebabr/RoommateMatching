import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getTopMatches, sendLike, getLikesSent, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function DiscoverPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [matchProfiles, setMatchProfiles] = useState([]);
  const [likedIds, setLikedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [likingId, setLikingId] = useState(null);
  const [modal, setModal] = useState(null);

  const loadMatches = async () => {
    if (!user?.id) return;
    try {
      const [data, sentIds] = await Promise.all([getTopMatches(user.id), getLikesSent(user.id)]);
      const topList = data.matches || [];
      setLikedIds(new Set(sentIds));
      const profiles = await Promise.all(
        topList.map(async (m) => {
          try { const p = await getUser(m.user_id); return { ...p, compatibilityScore: m.compatibilityScore }; }
          catch { return { id: m.user_id, username: `User #${m.user_id}`, compatibilityScore: m.compatibilityScore }; }
        })
      );
      setMatchProfiles(profiles);
    } catch { setMatchProfiles([]); }
  };

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      await refreshUser();
      await loadMatches();
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [user?.id]);

  const handleLike = async (targetId) => {
    setLikingId(targetId);
    try {
      const result = await sendLike(user.id, targetId);
      if (result.status === 'matched') {
        setModal({ title: "🎉 It's a Match!", message: `You and User #${targetId} are now roommate matches!` });
        await refreshUser();
        await loadMatches();
      } else {
        setLikedIds(prev => new Set([...prev, targetId]));
      }
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send like.' });
    } finally {
      setLikingId(null);
    }
  };

  if (loading) return (
    <div style={S.centered}>
      <Spinner size={40} />
      <p style={{ color: Colors.textSecondary, marginTop: 16, fontSize: 14 }}>Finding compatible roommates...</p>
    </div>
  );

  return (
    <div style={{ backgroundColor: Colors.bg, minHeight: '100%' }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}
      <div style={S.header}>
        <div>
          <p style={S.headerTitle}>Discover</p>
          <p style={S.headerSub}>{matchProfiles.length} compatible roommates</p>
        </div>
        <NotificationBell />
      </div>

      {matchProfiles.length === 0 ? (
        <div style={S.centered}>
          <span style={{ fontSize: 56 }}>🔍</span>
          <p style={S.emptyTitle}>No Matches Yet</p>
          <p style={S.emptySub}>New users are being added all the time. Pull down to refresh!</p>
          <button style={S.refreshBtn} onClick={() => { setRefreshing(true); loadMatches().finally(() => setRefreshing(false)); }}>
            {refreshing ? <Spinner size={16} color={Colors.black} /> : 'Refresh'}
          </button>
        </div>
      ) : (
        <div style={{ padding: '0 20px 30px' }}>
          {matchProfiles.map(item => {
            const score = item.compatibilityScore;
            const color = getCompatibilityColor(score);
            const label = getCompatibilityLabel(score);
            const myTags = user?.lifestyleTags || [];
            const theirTags = item.lifestyleTags || [];
            const sharedTags = myTags.filter(t => theirTags.includes(t));
            const photoSrc = getPhotoUrl(item.photoUrl);
            const pending = likedIds.has(item.id);

            return (
              <div key={item.id} style={S.card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14, padding: `5px 12px`, borderRadius: Radius.full, border: `1px solid ${color}`, backgroundColor: color + '20', alignSelf: 'flex-start' }}>
                  <span style={{ fontSize: 16, fontWeight: 800, color }}>{Math.round(score * 100)}%</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color }}>{label}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12, cursor: 'pointer' }} onClick={() => navigate(`/user/${item.id}`, { state: { score } })}>
                  {photoSrc ? (
                    <img src={photoSrc} alt="" style={S.avatarImg} />
                  ) : (
                    <div style={S.avatar}><span style={{ fontSize: 20, fontWeight: 800, color: Colors.accent }}>{(item.username || '?')[0].toUpperCase()}</span></div>
                  )}
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>{item.username || `User #${item.id}`}</p>
                    {item.gender && <p style={{ fontSize: 12, color: Colors.info, fontWeight: 600, margin: '2px 0 0' }}>{item.gender === 'male' ? '♂ Male' : '♀ Female'}</p>}
                    {item.bio ? (
                      <p style={{ fontSize: 13, color: Colors.textSecondary, margin: '2px 0 0', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{item.bio}</p>
                    ) : (
                      <p style={{ fontSize: 12, color: Colors.textMuted, margin: '2px 0 0' }}>ID: {item.id}</p>
                    )}
                  </div>
                </div>

                {theirTags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                    {theirTags.slice(0, 6).map(tag => {
                      const shared = sharedTags.includes(tag);
                      return (
                        <span key={tag} style={{ padding: '3px 8px', borderRadius: Radius.full, border: `1px solid ${shared ? Colors.success : Colors.border}`, backgroundColor: shared ? Colors.successDim : Colors.bgCardLight, fontSize: 11, fontWeight: 600, color: shared ? Colors.success : Colors.textMuted }}>
                          {tag}
                        </span>
                      );
                    })}
                    {theirTags.length > 6 && <span style={{ fontSize: 11, color: Colors.textMuted, alignSelf: 'center' }}>+{theirTags.length - 6}</span>}
                  </div>
                )}

                {sharedTags.length > 0 && (
                  <p style={{ fontSize: 12, fontWeight: 600, color: Colors.success, margin: '0 0 10px' }}>
                    {sharedTags.length} shared {sharedTags.length === 1 ? 'interest' : 'interests'}
                  </p>
                )}

                <div style={{ marginBottom: 16 }}>
                  {CATEGORIES.map(cat => {
                    const pref = item[cat.key];
                    if (!pref) return null;
                    const pct = (pref.value / cat.max) * 100;
                    const shortLabel = cat.label.replace(' (Weekdays)', ' WD').replace(' (Weekends)', ' WE').replace('Smoking / Substances', 'Smoking');
                    return (
                      <div key={cat.key} style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, color: Colors.textMuted, width: 80, flexShrink: 0, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{shortLabel}</span>
                        <div style={{ flex: 1, height: 4, backgroundColor: Colors.border, borderRadius: 2, margin: '0 8px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, backgroundColor: Colors.accent, borderRadius: 2 }} />
                        </div>
                        <span style={{ fontSize: 11, color: Colors.textSecondary, width: 20, textAlign: 'right' }}>{Math.round(pref.value)}</span>
                      </div>
                    );
                  })}
                </div>

                {pending ? (
                  <div style={S.pendingBtn}><span style={{ fontSize: 15, fontWeight: 600, color: Colors.textMuted }}>✓ Pending</span></div>
                ) : (
                  <button style={S.likeBtn} onClick={() => handleLike(item.id)} disabled={likingId === item.id}>
                    {likingId === item.id ? <Spinner size={18} color={Colors.black} /> : '♥ Like'}
                  </button>
                )}
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
  card:       { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 20, marginTop: 16, border: `1px solid ${Colors.border}`, display: 'flex', flexDirection: 'column' },
  avatar:     { width: 48, height: 48, borderRadius: '50%', backgroundColor: Colors.accentGlow, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14, border: `2px solid ${Colors.accent}`, flexShrink: 0 },
  avatarImg:  { width: 48, height: 48, borderRadius: '50%', objectFit: 'cover', marginRight: 14, border: `2px solid ${Colors.accent}`, flexShrink: 0 },
  likeBtn:    { width: '100%', backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '12px 0', fontSize: 15, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  pendingBtn: { width: '100%', border: `1.5px solid ${Colors.border}`, borderRadius: Radius.md, padding: '12px 0', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  centered:   { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40, minHeight: '60vh' },
  emptyTitle: { fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: '16px 0 8px' },
  emptySub:   { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: '20px', margin: 0 },
  refreshBtn: { marginTop: 24, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '12px 32px', fontSize: 15, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 },
};
