import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors } from '../utils/theme';
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
    <div className="loading-page">
      <Spinner size={40} />
      <p className="text-secondary" style={{ fontSize: 14, margin: 0 }}>Loading matches...</p>
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}

      <div className="page-container">
        <div className="page-header">
          <div>
            <p className="page-header-title">Matches</p>
            <p className="page-header-sub">{matches.length} confirmed {matches.length === 1 ? 'match' : 'matches'}</p>
          </div>
          <NotificationBell />
        </div>

        {matches.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize: 56 }}>🏠</span>
            <p className="empty-state-title">No Matches Yet</p>
            <p className="empty-state-desc">When you and someone like each other, you'll see them here.</p>
          </div>
        ) : (
          <div className="matches-grid">
            {matches.map((item, i) => {
              const p = item.profile;
              const score = item.compatibilityScore;
              const photoSrc = getPhotoUrl(p?.photoUrl);

              return (
                <div key={item._id || i} className="matches-card">
                  <div className="matches-card-header">
                    <span style={{ fontSize: 20 }}>🤝</span>
                    <span className="matches-label">Roommate Match</span>
                    {score !== null && (
                      <span className="matches-score-badge">
                        {Math.round(score * 100)}% compatible
                      </span>
                    )}
                  </div>

                  <div className="matches-user-row" onClick={() => navigate(`/user/${p.id}`, { state: { score } })}>
                    {photoSrc ? (
                      <img src={photoSrc} alt="" className="matches-avatar-img" />
                    ) : (
                      <div className="matches-avatar">
                        <span className="avatar-letter-success" style={{ fontSize: 24 }}>{(p.username || '?')[0].toUpperCase()}</span>
                      </div>
                    )}
                    <div>
                      <p className="matches-username">{p.username || `User #${p.id}`}</p>
                      <p className="matches-user-id">ID: {p.id}</p>
                    </div>
                  </div>

                  {p.sleepScoreWD && (
                    <div className="matches-comparison">
                      <p className="matches-comparison-title">Preference Comparison</p>
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
                          <div key={cat.key} className="matches-comp-row">
                            <span className="matches-comp-label">{shortLabel}</span>
                            <div className="matches-comp-values">
                              <span className="matches-comp-mine">{Math.round(mine)}</span>
                              <span className="matches-comp-vs">vs</span>
                              <span className="matches-comp-theirs">{Math.round(theirs)}</span>
                            </div>
                            <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-full)', minWidth: 42, textAlign: 'center', backgroundColor: simBg, fontSize: 11, fontWeight: 700, color: simColor }}>
                              {sim}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  <div className="matches-actions">
                    <button className="matches-chat-btn" onClick={() => navigate(`/chat/${p.id}`, { state: { partnerName: p.username } })}>
                      💬 Chat
                    </button>
                    <button className="matches-unmatch-btn" onClick={() => handleUnmatch(p.id, p.username || `User #${p.id}`)}>
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
