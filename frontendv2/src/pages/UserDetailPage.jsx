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
    <div style={{ height: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.bg }}>
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
    <div style={{ minHeight: '100dvh', backgroundColor: Colors.bg, maxWidth: 600, margin: '0 auto' }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      <div style={{ padding: '20px 20px 8px' }}>
        <button style={{ background: 'none', border: 'none', fontSize: 16, color: Colors.accent, fontWeight: 600, cursor: 'pointer' }} onClick={() => navigate(-1)}>
          ← Back
        </button>
      </div>

      <div style={{ padding: '0 24px 60px' }}>
        {/* Profile header */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 28 }}>
          {photoSrc ? (
            <img src={photoSrc} alt="" style={{ width: 96, height: 96, borderRadius: '50%', objectFit: 'cover', border: `3px solid ${color}`, marginBottom: 14 }} />
          ) : (
            <div style={{ width: 96, height: 96, borderRadius: '50%', backgroundColor: Colors.bgCard, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `3px solid ${color}`, marginBottom: 14 }}>
              <span style={{ fontSize: 40, fontWeight: 800, color }}>{(profile.username || '?')[0].toUpperCase()}</span>
            </div>
          )}
          <p style={{ fontSize: 28, fontWeight: 800, color: Colors.textPrimary, margin: '0 0 4px' }}>{profile.username}</p>
          <p style={{ fontSize: 13, color: Colors.textMuted, margin: 0 }}>User ID: {profile.id}</p>

          {genderLabel && (
            <span style={{ marginTop: 8, backgroundColor: Colors.infoDim, padding: '5px 14px', borderRadius: Radius.full, border: `1px solid ${Colors.info}`, fontSize: 13, fontWeight: 600, color: Colors.info }}>
              {genderLabel}
            </span>
          )}

          {profile.bio && (
            <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', marginTop: 10, lineHeight: '20px', paddingLeft: 8, paddingRight: 8 }}>
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
            <p style={{ fontSize: 13, fontWeight: 600, color: Colors.success, marginTop: 8, marginBottom: 0 }}>
              {sharedTags.length} shared {sharedTags.length === 1 ? 'interest' : 'interests'} with you!
            </p>
          )}

          {profile.matched && (
            <span style={{ marginTop: 10, backgroundColor: Colors.infoDim, padding: '5px 14px', borderRadius: Radius.full, fontSize: 12, fontWeight: 600, color: Colors.info }}>
              Currently Matched
            </span>
          )}

          {score != null && (
            <div style={{ marginTop: 16, padding: '12px 24px', borderRadius: Radius.lg, border: `1px solid ${color}`, backgroundColor: color + '15', textAlign: 'center', width: '100%' }}>
              <p style={{ fontSize: 36, fontWeight: 800, color, margin: 0 }}>{Math.round(score * 100)}%</p>
              <p style={{ fontSize: 14, fontWeight: 600, color, margin: '2px 0 0' }}>Compatibility — {label}</p>
            </div>
          )}
        </div>

        {/* Preferences */}
        <p style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 14px' }}>Preferences</p>
        {CATEGORIES.map(cat => {
          const pref  = profile[cat.key];
          if (!pref) return null;
          const myPref = user?.[cat.key];
          const pct   = (pref.value / cat.max) * 100;
          return (
            <div key={cat.key} style={{ backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: 16, marginBottom: 10, border: `1px solid ${Colors.border}` }}>
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

        {canLike && (
          <button style={{ width: '100%', backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '16px 0', fontSize: 16, fontWeight: 700, color: Colors.black, border: 'none', marginTop: 20, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={handleLike} disabled={liking}>
            {liking ? <Spinner size={20} color={Colors.black} /> : '♥ Send Like'}
          </button>
        )}
      </div>
    </div>
  );
}
