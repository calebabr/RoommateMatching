import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Colors } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import posthog from 'posthog-js';
import { getUser, getMatchScore, sendLike, getLikesSent, getPhotoUrl, blockUser, reportUser } from '../services/api';
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
  const [liking,        setLiking]        = useState(false);
  const [blocking,      setBlocking]      = useState(false);
  const [modal,         setModal]         = useState(null);
  const [alreadyLiked,  setAlreadyLiked]  = useState(false);
  const [alreadyMatched,setAlreadyMatched]= useState(false);
  const [showBlockConfirm, setShowBlockConfirm] = useState(false);
  const [showReportModal,  setShowReportModal]  = useState(false);
  const [reportReason,     setReportReason]     = useState('harassment');
  const [reportDesc,       setReportDesc]       = useState('');
  const [reporting,        setReporting]        = useState(false);
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
        if (active && user) {
          const matchedWith = user?.matchedWith || [];
          setAlreadyMatched(Array.isArray(matchedWith) ? matchedWith.includes(userIdNum) : matchedWith === userIdNum);
          try {
            const likes = await getLikesSent(user.id);
            const likedIds = likes.map(l => l.toUser ?? l.to_user ?? l);
            setAlreadyLiked(likedIds.includes(userIdNum));
          } catch {}
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
        setAlreadyMatched(true);
        posthog.capture('match_created', { matched_user_id: userIdNum });
        setModal({ title: '🎉 Match!', message: `You and ${profile?.username || 'this user'} are now roommate matches!` });
      } else {
        setAlreadyLiked(true);
        posthog.capture('like_sent', { target_user_id: userIdNum });
        setModal({ title: 'Like Sent!', message: "They'll see your interest." });
      }
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send like.' });
    } finally {
      setLiking(false);
    }
  };

  const handleBlock = async () => {
    setBlocking(true);
    try {
      await blockUser(userIdNum);
      navigate('/discover');
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not block user.' });
    } finally {
      setBlocking(false);
      setShowBlockConfirm(false);
    }
  };

  const handleReport = async () => {
    setReporting(true);
    try {
      await reportUser(user.id, userIdNum, reportReason, reportDesc.trim() || undefined);
      setShowReportModal(false);
      setReportReason('harassment');
      setReportDesc('');
      setModal({ title: 'Reported', message: 'Thank you for your report. Our team will review it.' });
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not submit report.' });
    } finally {
      setReporting(false);
    }
  };

  if (loading) return (
    <div className="full-height flex-center bg-base">
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
  const canLike   = !alreadyLiked && !alreadyMatched && profile.id !== user?.id && matchCount < 5;

  return (
    <div className="full-height overflow-y bg-base">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      {/* Block confirmation */}
      {showBlockConfirm && (
        <div className="overlay-bg" onClick={() => setShowBlockConfirm(false)}>
          <div className="inline-modal userdetail-block-modal" onClick={e => e.stopPropagation()}>
            <p className="userdetail-modal-title">Block this user?</p>
            <p className="userdetail-modal-desc">
              They won't be able to see you and you won't see them.
            </p>
            <div className="userdetail-modal-actions">
              <button
                className="userdetail-block-confirm-btn"
                onClick={handleBlock}
                disabled={blocking}
              >
                {blocking ? '...' : 'Block'}
              </button>
              <button
                className="userdetail-modal-cancel-btn"
                onClick={() => setShowBlockConfirm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report modal */}
      {showReportModal && (
        <div className="overlay-bg" onClick={() => setShowReportModal(false)}>
          <div className="inline-modal userdetail-report-modal" onClick={e => e.stopPropagation()}>
            <p className="userdetail-report-modal-title">Report User</p>
            <label className="report-label">Reason</label>
            <select
              className="report-select"
              value={reportReason}
              onChange={e => setReportReason(e.target.value)}
            >
              <option value="harassment">Harassment</option>
              <option value="inappropriate_content">Inappropriate Content</option>
              <option value="fake_profile">Fake Profile</option>
              <option value="spam">Spam</option>
              <option value="underage">Underage User</option>
              <option value="other">Other</option>
            </select>
            <label className="report-label" style={{ marginTop: 12 }}>Description (optional)</label>
            <textarea
              className="report-textarea"
              value={reportDesc}
              onChange={e => setReportDesc(e.target.value)}
              maxLength={1000}
              placeholder="Provide additional details..."
            />
            <p className="report-char-count">{reportDesc.length}/1000</p>
            <div className="userdetail-modal-actions">
              <button
                className="report-submit-btn"
                onClick={handleReport}
                disabled={reporting}
              >
                {reporting ? '...' : 'Submit Report'}
              </button>
              <button
                className="report-cancel-btn"
                onClick={() => { setShowReportModal(false); setReportReason('harassment'); setReportDesc(''); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="userdetail-page">
        <button className="userdetail-back-btn" onClick={() => navigate(-1)}>← Back</button>

        <div className="two-col-layout">
          {/* Left: avatar + identity */}
          <div className="userdetail-left-col">
            <div className="userdetail-profile-card">
              {photoSrc ? (
                <img src={photoSrc} alt="" className="userdetail-avatar" />
              ) : (
                <div className="userdetail-avatar-fallback" style={{ borderColor: color }}>
                  <span style={{ fontSize: 40, fontWeight: 800, color }}>{(profile.username || '?')[0].toUpperCase()}</span>
                </div>
              )}

              <p className="userdetail-username">{profile.username}</p>
              <p className="userdetail-user-id">User ID: {profile.id}</p>

              {genderLabel && (
                <span className="userdetail-gender-badge">{genderLabel}</span>
              )}

              {profile.bio && (
                <p className="userdetail-bio">{profile.bio}</p>
              )}

              {(theirTags.length > 0 || profile.religionTag) && (
                <div className="userdetail-tags">
                  {theirTags.map(tag => {
                    const shared = sharedTags.includes(tag);
                    return (
                      <span
                        key={tag}
                        className={`tag-pill ${shared ? 'tag-pill-success' : 'tag-pill-neutral'}`}
                        style={{ fontSize: 12 }}
                      >
                        {tag}
                      </span>
                    );
                  })}
                  {profile.religionTag && (
                    <span className="tag-pill tag-pill-neutral" style={{ fontSize: 12 }}>
                      {profile.religionTag}
                    </span>
                  )}
                </div>
              )}

              {(profile.major || (profile.graduationSeason && profile.graduationYear)) && (
                <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {profile.major && (
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #A0A0A0)', margin: 0 }}>
                      {profile.major}
                    </p>
                  )}
                  {profile.graduationSeason && profile.graduationYear && (
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #A0A0A0)', margin: 0 }}>
                      Graduating {profile.graduationSeason} {profile.graduationYear}
                    </p>
                  )}
                </div>
              )}

              {sharedTags.length > 0 && (
                <p className="userdetail-shared-count">
                  {sharedTags.length} shared {sharedTags.length === 1 ? 'interest' : 'interests'} with you!
                </p>
              )}

              {score != null && (
                <div
                  className="userdetail-score-box"
                  style={{ border: `1px solid ${color}`, backgroundColor: color + '15' }}
                >
                  <p className="userdetail-score-pct" style={{ color }}>{Math.round(score * 100)}%</p>
                  <p className="userdetail-score-label" style={{ color }}>Compatibility — {label}</p>
                </div>
              )}

              {profile.matched && (
                <span className="userdetail-matched-badge">Currently Matched</span>
              )}

              {canLike && (
                <button className="userdetail-like-btn" onClick={handleLike} disabled={liking}>
                  {liking ? <Spinner size={20} color={Colors.black} /> : '♥ Send Like'}
                </button>
              )}
              {alreadyMatched && <span className="userdetail-already-matched">✓ Already matched</span>}
              {!alreadyMatched && alreadyLiked && <span className="userdetail-like-sent">Like sent</span>}

              {profile.id !== user?.id && (
                <div className="userdetail-mod-actions">
                  <button className="userdetail-block-btn" onClick={() => setShowBlockConfirm(true)}>Block</button>
                  <button className="userdetail-report-btn" onClick={() => setShowReportModal(true)}>Report</button>
                </div>
              )}
            </div>
          </div>

          {/* Right: preferences */}
          <div className="col-right-flex">
            <p className="userdetail-right-title">Preferences</p>
            <div className="userdetail-pref-grid">
              {CATEGORIES.map(cat => {
                const pref  = profile[cat.key];
                if (!pref) return null;
                const myPref = user?.[cat.key];
                const pct   = (pref.value / cat.max) * 100;
                return (
                  <div key={cat.key} className="userdetail-pref-card">
                    <div className="userdetail-pref-header">
                      <span className="userdetail-pref-name">{cat.label}</span>
                      {pref.isDealBreaker && (
                        <span className="userdetail-dealbreaker-badge">Deal-breaker</span>
                      )}
                    </div>
                    <p className="userdetail-pref-value">{cat.formatValue(pref.value)}</p>
                    <div className="userdetail-pref-bar-track">
                      <div className="userdetail-pref-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    {myPref && (
                      <div className="userdetail-pref-comparison">
                        <span className="userdetail-pref-mine">You: {cat.formatValue(myPref.value)}</span>
                        <span className="userdetail-pref-diff">Diff: {Math.abs(Math.round(pref.value - myPref.value))}</span>
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
