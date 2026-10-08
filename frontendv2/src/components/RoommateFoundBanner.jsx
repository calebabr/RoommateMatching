import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { undoRoommateFound } from '../services/api';

/**
 * Banner shown at the top of Discover and Likes while the "found a roommate"
 * status is active (P3FT.12). Renders nothing when the status is off.
 */
export default function RoommateFoundBanner() {
  const { user, refreshUser } = useAuth();
  const [undoing, setUndoing] = useState(false);
  const [error,   setError]   = useState('');

  if (!user?.roommateFound) return null;

  const handleUndo = async () => {
    setUndoing(true);
    setError('');
    try {
      await undoRoommateFound(user.id);
      await refreshUser();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not undo. Please try again.');
    } finally {
      setUndoing(false);
    }
  };

  return (
    <div className="roommate-found-banner" role="status">
      <span className="roommate-found-banner-emoji">🎉</span>
      <div className="roommate-found-banner-text">
        <p className="roommate-found-banner-title">You marked that you found a roommate</p>
        <p className="roommate-found-banner-desc">
          You're hidden from Discover and new likes. Your existing matches and chats still work.
        </p>
        {error && <p className="roommate-found-banner-error">{error}</p>}
      </div>
      <button
        className="roommate-found-banner-undo"
        onClick={handleUndo}
        disabled={undoing}
      >
        {undoing ? 'Undoing…' : 'Undo'}
      </button>
    </div>
  );
}
