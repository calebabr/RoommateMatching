import React, { useState, useEffect } from 'react';
import posthog from 'posthog-js';
import { useAuth } from '../context/AuthContext';
import { getMatches, getUser, getPhotoUrl, markRoommateFound } from '../services/api';
import Spinner from './Spinner';

/**
 * "I found a roommate 🎉" flow (P3FT.12).
 * Multi-select of the user's current matches plus a "Found them elsewhere" option.
 */
export default function RoommateFoundModal({ onClose, onDone }) {
  const { user, refreshUser } = useAuth();
  const [matches,   setMatches]   = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [selected,  setSelected]  = useState([]);
  const [elsewhere, setElsewhere] = useState(false);
  const [saving,    setSaving]    = useState(false);
  const [error,     setError]     = useState('');

  useEffect(() => {
    let active = true;
    (async () => {
      if (!user?.id) return;
      try {
        const raw = await getMatches(user.id);
        const enriched = await Promise.all(
          (raw || []).map(async (m) => {
            const partnerId = m.user1_id === user.id ? m.user2_id : m.user1_id;
            try {
              const p = await getUser(partnerId);
              return { id: partnerId, username: p.username || `User #${partnerId}`, photoUrl: p.photoUrl };
            } catch {
              return { id: partnerId, username: `User #${partnerId}`, photoUrl: null };
            }
          })
        );
        if (active) setMatches(enriched);
      } catch {
        if (active) setMatches([]);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [user?.id]);

  const togglePartner = (id) => {
    setElsewhere(false);
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const toggleElsewhere = () => {
    setElsewhere(prev => {
      const next = !prev;
      if (next) setSelected([]);
      return next;
    });
  };

  const canSubmit = (selected.length > 0 || elsewhere) && !saving;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSaving(true);
    setError('');
    const viaApp = !elsewhere && selected.length > 0;
    try {
      const result = await markRoommateFound(user.id, { partnerIds: elsewhere ? [] : selected, viaApp });
      posthog.capture('roommate_found', { viaApp });
      await refreshUser();
      onDone?.(result);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="overlay-bg overlay-bg--sheet" onClick={onClose}>
      <div className="inline-modal roommate-found-modal" onClick={e => e.stopPropagation()}>
        <p className="roommate-found-modal-title">I found a roommate 🎉</p>
        <p className="roommate-found-modal-desc">
          Congrats! Tell us who so we can hide you from Discover. Your existing matches and
          chats stay open, and you can undo this any time.
        </p>

        {loading ? (
          <div className="roommate-found-loading"><Spinner size={24} /></div>
        ) : (
          <div className="roommate-found-options">
            {matches.length === 0 ? (
              <p className="roommate-found-empty">You don't have any matches yet.</p>
            ) : (
              matches.map(m => {
                const checked  = selected.includes(m.id);
                const photoSrc = getPhotoUrl(m.photoUrl);
                return (
                  <button
                    key={m.id}
                    type="button"
                    className={`roommate-found-option ${checked ? 'roommate-found-option--selected' : ''}`}
                    onClick={() => togglePartner(m.id)}
                    aria-pressed={checked}
                  >
                    <span className={`roommate-found-check ${checked ? 'roommate-found-check--on' : ''}`}>
                      {checked ? '✓' : ''}
                    </span>
                    {photoSrc ? (
                      <img src={photoSrc} alt="" className="roommate-found-avatar-img" />
                    ) : (
                      <span className="roommate-found-avatar">{(m.username || '?')[0].toUpperCase()}</span>
                    )}
                    <span className="roommate-found-option-name">{m.username}</span>
                  </button>
                );
              })
            )}

            <button
              type="button"
              className={`roommate-found-option roommate-found-option--elsewhere ${elsewhere ? 'roommate-found-option--selected' : ''}`}
              onClick={toggleElsewhere}
              aria-pressed={elsewhere}
            >
              <span className={`roommate-found-check ${elsewhere ? 'roommate-found-check--on' : ''}`}>
                {elsewhere ? '✓' : ''}
              </span>
              <span className="roommate-found-avatar">🌎</span>
              <span className="roommate-found-option-name">Found them elsewhere</span>
            </button>
          </div>
        )}

        {error && <p className="roommate-found-error">{error}</p>}

        <div className="roommate-found-actions">
          <button
            className={`roommate-found-confirm ${!canSubmit ? 'roommate-found-confirm--disabled' : ''}`}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            {saving ? '...' : 'Confirm'}
          </button>
          <button className="roommate-found-cancel" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
