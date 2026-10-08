import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import posthog from 'posthog-js';
import { Colors } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getTopMatches, sendLike, getLikesSent, skipUser, getUser, getPhotoUrl } from '../services/api';
import {
  EMPTY_FILTERS,
  loadFilters,
  saveFilters,
  normalizeFilters,
  activeFilterKeys,
  countActiveFilters,
} from '../utils/discoverFilters';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';
import RoommateFoundBanner from '../components/RoommateFoundBanner';
import DiscoverFilterBar from '../components/DiscoverFilterBar';
import PromptCards from '../components/PromptCards';

export default function DiscoverPage() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [matchProfiles, setMatchProfiles] = useState([]);
  const [likedIds,  setLikedIds]  = useState(new Set());
  const [loading,   setLoading]   = useState(true);
  const [refreshing,setRefreshing]= useState(false);
  const [likingId,  setLikingId]  = useState(null);
  const [passingId, setPassingId] = useState(null);
  const [modal,     setModal]     = useState(null);
  // P3FT.16 — filters are restored from localStorage per user, never from the URL.
  const [filters,    setFilters]    = useState(() => loadFilters(user?.id));
  const [filteredOut,setFilteredOut]= useState(0);
  const [loadError,  setLoadError]  = useState(false);
  const initialisedRef = useRef(false);

  const loadMatches = async (activeFilters) => {
    if (!user?.id) return;
    try {
      const [data, sentIds] = await Promise.all([
        getTopMatches(user.id, activeFilters),
        getLikesSent(user.id),
      ]);
      const topList = data.matches || [];
      // Filters that exclude everyone come back as 200 {matches: [], filteredOut: N} —
      // an empty result, not an error.
      setFilteredOut(data.filteredOut || 0);
      setLoadError(false);
      setLikedIds(new Set(sentIds));
      const profiles = await Promise.all(
        topList.map(async (m) => {
          try { const p = await getUser(m.user_id); return { ...p, compatibilityScore: m.compatibilityScore }; }
          catch { return { id: m.user_id, username: `User #${m.user_id}`, compatibilityScore: m.compatibilityScore }; }
        })
      );
      setMatchProfiles(profiles);
    } catch {
      setMatchProfiles([]);
      setFilteredOut(0);
      setLoadError(true);
    }
  };

  const applyFilters = (next) => {
    const normalized = normalizeFilters(next);
    setFilters(normalized);
    saveFilters(user?.id, normalized);
    const keys = activeFilterKeys(normalized);
    if (keys.length > 0) {
      // Keys only — filter VALUES (religion, budget) never leave the device.
      posthog.capture('discover_filter_applied', { filter_keys: keys, filter_count: keys.length });
    }
  };

  useEffect(() => {
    if (!user?.id) return;
    let active = true;
    (async () => {
      setLoading(true);
      if (!initialisedRef.current) await refreshUser();
      await loadMatches(filters);
      initialisedRef.current = true;
      if (active) setLoading(false);
    })();
    return () => { active = false; };
  }, [user?.id, filters]);

  const handleLike = async (targetId) => {
    setLikingId(targetId);
    try {
      const result = await sendLike(user.id, targetId);
      if (result.status === 'matched') {
        setModal({ title: "🎉 It's a Match!", message: `You and User #${targetId} are now roommate matches!` });
        await refreshUser(); await loadMatches(filters);
      } else {
        setLikedIds(prev => new Set([...prev, targetId]));
      }
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not send like.' });
    } finally { setLikingId(null); }
  };

  const handlePass = async (targetId) => {
    setPassingId(targetId);
    try {
      await skipUser(user.id, targetId);
      setMatchProfiles(prev => prev.filter(p => p.id !== targetId));
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not pass on this profile.' });
    } finally {
      setPassingId(null);
    }
  };

  const hasActiveFilters = countActiveFilters(filters) > 0;

  if (loading) return (
    <div className="loading-page">
      <Spinner size={40} />
      <p className="text-secondary" style={{ fontSize: 14, margin: 0 }}>Finding compatible roommates...</p>
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} />}

      <div className="page-container">
        <RoommateFoundBanner />

        <div className="page-header">
          <div>
            <p className="page-header-title">Discover</p>
            <p className="page-header-sub">{matchProfiles.length} compatible roommates</p>
          </div>
          <div className="discover-header-actions">
            <button className="discover-refresh-btn" onClick={() => { setRefreshing(true); loadMatches(filters).finally(() => setRefreshing(false)); }} disabled={refreshing}>
              {refreshing ? <Spinner size={14} color={Colors.black} /> : '↻ Refresh'}
            </button>
            <NotificationBell />
          </div>
        </div>

        <DiscoverFilterBar
          filters={filters}
          onChange={applyFilters}
          resultCount={matchProfiles.length}
          filteredOut={filteredOut}
          loading={refreshing}
        />

        {matchProfiles.length === 0 ? (
          loadError ? (
            <div className="empty-state">
              <span className="empty-state-emoji">⚠️</span>
              <p className="empty-state-title">Couldn't Load Matches</p>
              <p className="empty-state-desc">Something went wrong on our side. Try Refresh in a moment.</p>
            </div>
          ) : hasActiveFilters ? (
            <div className="empty-state">
              <span className="empty-state-emoji">🎛️</span>
              <p className="empty-state-title">No one matches these filters</p>
              <p className="empty-state-desc">
                {filteredOut > 0
                  ? `${filteredOut} ${filteredOut === 1 ? 'person was' : 'people were'} hidden by your filters. Try widening them.`
                  : 'Try widening your filters to see more people.'}
              </p>
              <div className="discover-filter-empty-actions">
                <button className="discover-filter-empty-btn" onClick={() => applyFilters({ ...EMPTY_FILTERS })}>
                  Clear all filters
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <span className="empty-state-emoji">🔍</span>
              <p className="empty-state-title">No Matches Yet</p>
              <p className="empty-state-desc">New users are being added all the time. Hit Refresh!</p>
            </div>
          )
        ) : (
          <div className="discover-grid">
            {matchProfiles.map(item => {
              const score    = item.compatibilityScore;
              const color    = getCompatibilityColor(score);
              const label    = getCompatibilityLabel(score);
              const myTags   = user?.lifestyleTags || [];
              const theirTags= item.lifestyleTags || [];
              const shared   = myTags.filter(t => theirTags.includes(t));
              const photoSrc = getPhotoUrl(item.photoUrl);
              const pending  = likedIds.has(item.id);

              return (
                <div key={item.id} className="discover-card">
                  {/* Score badge */}
                  <div
                    className="discover-score-badge"
                    style={{ border: `1px solid ${color}`, backgroundColor: color + '20' }}
                  >
                    <span style={{ fontSize: 15, fontWeight: 800, color }}>{Math.round(score * 100)}%</span>
                    <span style={{ fontSize: 11, fontWeight: 600, color }}>{label}</span>
                  </div>

                  {/* User info */}
                  <div className="discover-user-row" onClick={() => navigate(`/user/${item.id}`, { state: { score } })}>
                    {photoSrc ? (
                      <img src={photoSrc} alt="" className="discover-avatar-img" />
                    ) : (
                      <div className="discover-avatar">
                        <span className="avatar-letter-accent">{(item.username || '?')[0].toUpperCase()}</span>
                      </div>
                    )}
                    <div style={{ flex: 1 }}>
                      <p className="discover-username">{item.username || `User #${item.id}`}</p>
                      {item.gender && <p className="discover-gender">{item.gender === 'male' ? '♂ Male' : '♀ Female'}</p>}
                      {item.bio && <p className="discover-bio">{item.bio}</p>}
                    </div>
                  </div>

                  {/* Prompt answers (P3FT.14) — below the bio */}
                  <PromptCards answers={item.promptAnswers} variant="compact" max={2} />

                  {/* Tags */}
                  {theirTags.length > 0 && (
                    <div className="discover-tags">
                      {theirTags.slice(0, 6).map(tag => (
                        <span
                          key={tag}
                          className={`tag-pill ${shared.includes(tag) ? 'tag-pill-success' : ''}`}
                          style={!shared.includes(tag) ? {
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-full)',
                            border: '1px solid var(--color-border)',
                            backgroundColor: 'var(--color-bg-card-light)',
                            fontSize: 11,
                            fontWeight: 600,
                            color: 'var(--color-text-muted)',
                          } : { padding: '2px 8px', fontSize: 11 }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {shared.length > 0 && <p className="discover-shared-count">{shared.length} shared {shared.length === 1 ? 'interest' : 'interests'}</p>}

                  {/* Pref bars */}
                  <div className="discover-pref-bars">
                    {CATEGORIES.map(cat => {
                      const pref = item[cat.key];
                      if (!pref) return null;
                      const pct = (pref.value / cat.max) * 100;
                      const short = cat.label.replace(' (Weekdays)', ' WD').replace(' (Weekends)', ' WE').replace('Smoking / Substances', 'Smoking');
                      return (
                        <div key={cat.key} className="discover-pref-row">
                          <span className="discover-pref-label">{short}</span>
                          <div className="discover-pref-bar-track">
                            <div className="discover-pref-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="discover-pref-value">{Math.round(pref.value)}</span>
                        </div>
                      );
                    })}
                  </div>

                  <div className="discover-card-actions">
                    {pending ? (
                      <div className="discover-pending" style={{ flex: 1 }}>
                        <span className="discover-pending-text">✓ Pending</span>
                      </div>
                    ) : (
                      <button className="discover-like-btn" onClick={() => handleLike(item.id)} disabled={likingId === item.id || passingId === item.id}>
                        {likingId === item.id ? <Spinner size={16} color={Colors.black} /> : '♥ Like'}
                      </button>
                    )}
                    <button
                      className="discover-pass-btn"
                      onClick={() => handlePass(item.id)}
                      disabled={passingId === item.id || likingId === item.id}
                    >
                      {passingId === item.id ? <Spinner size={16} color="var(--color-text-muted)" /> : '✕ Pass'}
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
