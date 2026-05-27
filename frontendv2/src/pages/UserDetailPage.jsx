import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getUser, getMatchScore, sendLike, getPhotoUrl } from '../services/api';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function UserDetailPage() {
  const navigate = useNavigate();
  const { userId } = useParams();
  const { state }  = useLocation();
  const { user }   = useAuth();
  const [profile, setProfile] = useState(null);
  const [score,   setScore]   = useState(state?.score ?? null);
  const [loading, setLoading] = useState(true);
  const [liking,  setLiking]  = useState(false);
  const [modal,   setModal]   = useState(null);
  const userIdNum = parseInt(userId, 10);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const p = await getUser(userIdNum);
        if (active) setProfile(p);
        if (score == null && user?.id) {
          try { const s = await getMatchScore(user.id, userIdNum); if (active) setScore(s.compatibilityScore); } catch {}
        }
      } catch {
        setModal({ title: 'Error', message: 'Could not load user profile.' });
        navigate(-1);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [userIdNum]);

  const handleLike = async () => {
    setLiking(true);
    try {
      const result = await sendLike(user.id, userIdNum);
      if (result.status === 'matched') {
        setModal({ title: '🎉 Match!', message: `You and ${profile?.username || 'this user'} are now roommate matches!` });
      } else {
        setModal({ title: 'Like Sent!', message: "They'll see your interest." });
      }
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send like.' });
    } finally {
      setLiking(false);
    }
  };

  if (loading) return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.bg }}>
      <Spinner size={40} />
    </div>
  );

  if (!profile) return null;

  const color     = score != null ? getCompatibilityColor(score) : Colors.textMuted;
  const label     = score != null ? getCompatibilityLabel(score) : '';
  const myTags    = user?.lifestyleTags || [];
  const theirTags = profile.lifestyleTags || [];
  const sharedTags= myTags.filter(t => theirTags.includes(t));
  const genderLabel = profile.gender === 'female' ? '♀ Female' : profile.gender === 'male' ? '♂ Male' : '';
  const photoSrc  = getPhotoUrl(profile.photoUrl);
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const canLike   = !profile.matched && profile.id !== user?.id && matchCount < 5;

  return (
    <div style={{ height: '100%', overflowY: 'auto', backgroundColor: Colors.bg }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      <div style={S.page}>
        <button style={S.backBtn} onClick={() => navigate(-1)}>← Back</button>

        <div style={S.cols}>
          {/* Left: avatar + identity */}
          <div style={S.leftCol}>
            <div style={S.profileCard}>
              {photoSrc ? (
                <img src={photoSrc} alt="" style={S.avatar} />
              ) : (
                <div style={{ ...S.avatarFallback, borderColor: color }}>
                  <span style={{ fontSize: 40, fontWeight: 800, color }}>{(profile.username || '?')[0].toUpperCase()}</span>
                </div>
              )}

              <p style={{ fontSize: 26, fontWeight: 800, color: Colors.textPrimary, margin: '0 0 4px', textAlign: 'center' }}>{profile.username}</p>
              <p style={{ fontSize: 13, color: Colors.textMuted, margin: 0 }}>User ID: {profile.id}</p>

              {genderLabel && (
                <span style={{ marginTop: 10, backgroundColor: Colors.infoDim, padding: '5px 14px', borderRadius: Radius.full, border: `1px solid ${Colors.info}`, fontSize: 13, fontWeight: 600, color: Colors.info }}>
                  {genderLabel}
                </span>
              )}

              {profile.bio && (
                <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', marginTop: 12, lineHeight: '20px' }}>
                  {profile.bio}
                </p>
              )}

              {theirTags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginTop: 12 }}>
                  {theirTags.map(tag => {
                    const shared = sharedTags.includes(tag);
                    return (
                      <span key={tag} style={{ padding: '4px 10px', borderRadius: Radius.full, border: `1px solid ${shared ? Colors.success : Colors.border}`, backgroundColor: shared ? Colors.successDim : Colors.bgCard, fontSize: 12, fontWeight: 600, color: shared ? Colors.success : Colors.textSecondary }}>
                        {tag}
                      </span>
                    );
                  })}
                </div>
              )}

              {sharedTags.length > 0 && (
                <p style={{ fontSize: 13, fontWeight: 600, color: Colors.success, marginTop: 10, marginBottom: 0, textAlign: 'center' }}>
                  {sharedTags.length} shared {sharedTags.length === 1 ? 'interest' : 'interests'} with you!
                </p>
              )}

              {score != null && (
                <div style={{ marginTop: 16, padding: '14px 20px', borderRadius: Radius.lg, border: `1px solid ${color}`, backgroundColor: color + '15', textAlign: 'center', width: '100%' }}>
                  <p style={{ fontSize: 38, fontWeight: 800, color, margin: 0 }}>{Math.round(score * 100)}%</p>
                  <p style={{ fontSize: 14, fontWeight: 600, color, margin: '2px 0 0' }}>Compatibility — {label}</p>
                </div>
              )}

              {profile.matched && (
                <span style={{ marginTop: 12, backgroundColor: Colors.infoDim, padding: '5px 14px', borderRadius: Radius.full, fontSize: 12, fontWeight: 600, color: Colors.info }}>
                  Currently Matched
                </span>
              )}

              {canLike && (
                <button style={S.likeBtn} onClick={handleLike} disabled={liking}>
                  {liking ? <Spinner size={20} color={Colors.black} /> : '♥ Send Like'}
                </button>
              )}
            </div>
          </div>

          {/* Right: preferences */}
          <div style={S.rightCol}>
            <p style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 16px' }}>Preferences</p>
            <div style={S.prefGrid}>
              {CATEGORIES.map(cat => {
                const pref  = profile[cat.key];
                if (!pref) return null;
                const myPref = user?.[cat.key];
                const pct   = (pref.value / cat.max) * 100;
                return (
                  <div key={cat.key} style={S.prefCard}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: Colors.textPrimary }}>{cat.label}</span>
                      {pref.isDealBreaker && (
                        <span style={{ backgroundColor: Colors.dangerDim, padding: '2px 8px', borderRadius: Radius.full, fontSize: 10, fontWeight: 700, color: Colors.danger, textTransform: 'uppercase' }}>Deal-breaker</span>
                      )}
                    </div>
                    <p style={{ fontSize: 15, fontWeight: 700, color: Colors.accent, margin: '0 0 8px' }}>{cat.formatValue(pref.value)}</p>
                    <div style={{ height: 6, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden', marginBottom: 8 }}>
                      <div style={{ height: '100%', width: `${pct}%`, backgroundColor: Colors.accent, borderRadius: 3 }} />
                    </div>
                    {myPref && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                        <span style={{ fontSize: 12, color: Colors.textMuted }}>You: {cat.formatValue(myPref.value)}</span>
                        <span style={{ fontSize: 12, color: Colors.textSecondary, fontWeight: 600 }}>Diff: {Math.abs(Math.round(pref.value - myPref.value))}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const S = {
  page:        { padding: '28px 32px 60px' },
  backBtn:     { background: 'none', border: 'none', fontSize: 15, color: Colors.accent, fontWeight: 600, cursor: 'pointer', marginBottom: 20, padding: 0 },
  cols:        { display: 'flex', gap: 28, alignItems: 'flex-start' },
  leftCol:     { width: 300, flexShrink: 0 },
  rightCol:    { flex: 1, minWidth: 0 },
  profileCard: { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 24, border: `1px solid ${Colors.border}`, display: 'flex', flexDirection: 'column', alignItems: 'center' },
  avatar:      { width: 96, height: 96, borderRadius: '50%', objectFit: 'cover', border: `3px solid ${Colors.accent}`, marginBottom: 14 },
  avatarFallback: { width: 96, height: 96, borderRadius: '50%', backgroundColor: Colors.bgCard, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `3px solid ${Colors.accent}`, marginBottom: 14 },
  likeBtn:     { width: '100%', marginTop: 16, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '14px 0', fontSize: 16, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  prefGrid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
  prefCard:    { backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: 16, border: `1px solid ${Colors.border}` },
};
