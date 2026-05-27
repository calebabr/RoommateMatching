import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getMatches, getUser, unmatchUser, getMatchScore, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function MatchesPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [matches,  setMatches]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [modal,    setModal]    = useState(null);

  const loadMatches = async () => {
    if (!user?.id) return;
    try {
      const raw = await getMatches(user.id);
      const enriched = await Promise.all(
        raw.map(async (match) => {
          const partnerId = match.user1_id === user.id ? match.user2_id : match.user1_id;
          try {
            const profile = await getUser(partnerId);
            let score = null;
            try { const s = await getMatchScore(user.id, partnerId); score = s.compatibilityScore; } catch {}
            return { ...match, profile, compatibilityScore: score };
          } catch {
            return { ...match, profile: { id: partnerId, username: `User #${partnerId}` }, compatibilityScore: null };
          }
        })
      );
      setMatches(enriched);
    } catch { setMatches([]); }
  };

  useEffect(() => {
    let active = true;
    (async () => { setLoading(true); await refreshUser(); await loadMatches(); if (active) setLoading(false); })();
    return () => { active = false; };
  }, [user?.id]);

  const handleUnmatch = (partnerId, partnerName) => {
    setModal({
      title: 'Unmatch',
      message: `Are you sure you want to unmatch with ${partnerName}? You'll both return to the matching pool.`,
      danger: true,
      confirmText: 'Unmatch',
      onConfirm: async () => {
        try {
          await unmatchUser(user.id, partnerId);
          await refreshUser();
          await loadMatches();
          setModal({ title: 'Unmatched', message: 'You are back in the matching pool.' });
        } catch (err) {
          setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not unmatch.' });
        }
      },
    });
  };

  if (loading) return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
      <Spinner size={40} />
      <p style={{ color: Colors.textSecondary, fontSize: 14, margin: 0 }}>Loading matches...</p>
    </div>
  );

  return (
    <div style={{ height: '100%', overflowY: 'auto', backgroundColor: Colors.bg }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}

      <div style={S.page}>
        <div style={S.header}>
          <div>
            <p style={S.headerTitle}>Matches</p>
            <p style={S.headerSub}>{matches.length} confirmed {matches.length === 1 ? 'match' : 'matches'}</p>
          </div>
          <NotificationBell />
        </div>

        {matches.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12 }}>
            <span style={{ fontSize: 56 }}>🏠</span>
            <p style={{ fontSize: 22, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>No Matches Yet</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: '20px', margin: 0 }}>When you and someone like each other, you'll see them here.</p>
          </div>
        ) : (
          <div style={S.grid}>
            {matches.map((item, i) => {
              const p = item.profile;
              const score = item.compatibilityScore;
              const photoSrc = getPhotoUrl(p?.photoUrl);

              return (
                <div key={item._id || i} style={S.card}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                    <span style={{ fontSize: 20 }}>🤝</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: Colors.success }}>Roommate Match</span>
                    {score !== null && (
                      <span style={{ marginLeft: 'auto', backgroundColor: Colors.successDim, padding: '3px 10px', borderRadius: Radius.full, fontSize: 12, fontWeight: 600, color: Colors.success }}>
                        {Math.round(score * 100)}% compatible
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, cursor: 'pointer' }} onClick={() => navigate(`/user/${p.id}`, { state: { score } })}>
                    {photoSrc ? (
                      <img src={photoSrc} alt="" style={S.avatarImg} />
                    ) : (
                      <div style={S.avatar}><span style={{ fontSize: 24, fontWeight: 800, color: Colors.success }}>{(p.username || '?')[0].toUpperCase()}</span></div>
                    )}
                    <div>
                      <p style={{ fontSize: 20, fontWeight: 700, color: Colors.textPrimary, margin: 0 }}>{p.username || `User #${p.id}`}</p>
                      <p style={{ fontSize: 12, color: Colors.textMuted, margin: '2px 0 0' }}>ID: {p.id}</p>
                    </div>
                  </div>

                  {p.sleepScoreWD && (
                    <div style={S.comparison}>
                      <p style={{ fontSize: 13, fontWeight: 700, color: Colors.textSecondary, margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: 0.6 }}>Preference Comparison</p>
                      {CATEGORIES.map(cat => {
                        const mine   = user[cat.key]?.value;
                        const theirs = p[cat.key]?.value;
                        if (mine == null || theirs == null) return null;
                        const diff = Math.abs(mine - theirs);
                        const maxDiff = cat.max - cat.min;
                        const sim = Math.round(((maxDiff - diff) / maxDiff) * 100);
                        const simColor = sim >= 80 ? Colors.success : sim >= 50 ? Colors.accent : Colors.danger;
                        const simBg    = sim >= 80 ? Colors.successDim : sim >= 50 ? Colors.accentGlow : Colors.dangerDim;
                        const shortLabel = cat.label.replace(' (Weekdays)', ' WD').replace(' (Weekends)', ' WE');
                        return (
                          <div key={cat.key} style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                            <span style={{ flex: 1, fontSize: 12, color: Colors.textMuted }}>{shortLabel}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginRight: 10 }}>
                              <span style={{ fontSize: 13, fontWeight: 700, color: Colors.accent }}>{Math.round(mine)}</span>
                              <span style={{ fontSize: 10, color: Colors.textMuted }}>vs</span>
                              <span style={{ fontSize: 13, fontWeight: 700, color: Colors.info }}>{Math.round(theirs)}</span>
                            </div>
                            <span style={{ padding: '2px 8px', borderRadius: Radius.full, minWidth: 42, textAlign: 'center', backgroundColor: simBg, fontSize: 11, fontWeight: 700, color: simColor }}>
                              {sim}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 10, marginTop: 'auto' }}>
                    <button style={S.chatBtn} onClick={() => navigate(`/chat/${p.id}`, { state: { partnerName: p.username } })}>
                      💬 Chat
                    </button>
                    <button style={S.unmatchBtn} onClick={() => handleUnmatch(p.id, p.username || `User #${p.id}`)}>
                      Unmatch
                    </button>
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
  page:       { padding: '28px 32px 40px' },
  header:     { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  headerTitle:{ fontSize: 24, fontWeight: 800, color: Colors.textPrimary, margin: 0 },
  headerSub:  { fontSize: 13, color: Colors.textSecondary, margin: '2px 0 0' },
  grid:       { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16 },
  card:       { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 20, border: `1px solid ${Colors.success}`, display: 'flex', flexDirection: 'column' },
  avatar:     { width: 56, height: 56, borderRadius: '50%', backgroundColor: Colors.successDim, display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: 14, border: `2px solid ${Colors.success}`, flexShrink: 0 },
  avatarImg:  { width: 56, height: 56, borderRadius: '50%', objectFit: 'cover', marginRight: 14, border: `2px solid ${Colors.success}`, flexShrink: 0 },
  comparison: { backgroundColor: Colors.bgCardLight, borderRadius: Radius.md, padding: 16, marginBottom: 16 },
  chatBtn:    { flex: 1, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer' },
  unmatchBtn: { flex: 1, backgroundColor: 'transparent', border: `1.5px solid ${Colors.danger}`, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 600, color: Colors.danger, cursor: 'pointer' },
};
