import React, { useState, useCallback } from 'react';
import { getMatchBreakdown } from '../services/api';
import { getCompatibilityColor } from '../utils/categories';
import { breakdownSentence, formatYourValue, normalizeScore, DIFFERENCE_LABEL } from '../utils/breakdown';
import Spinner from './Spinner';

/**
 * Collapsible "Why this score" panel (P3FT.11).
 * Data is fetched lazily the first time the panel is opened.
 */
export default function ScoreBreakdown({ userId, otherId }) {
  const [open,       setOpen]       = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState('');
  const [breakdown,  setBreakdown]  = useState(null);

  const toggle = useCallback(async () => {
    const next = !open;
    setOpen(next);
    if (!next || breakdown || loading) return;
    setLoading(true);
    setError('');
    try {
      const data = await getMatchBreakdown(userId, otherId);
      setBreakdown(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load the score breakdown.');
    } finally {
      setLoading(false);
    }
  }, [open, breakdown, loading, userId, otherId]);

  const categories = breakdown?.categories || [];

  return (
    <div className="breakdown">
      <button
        type="button"
        className="breakdown-toggle"
        onClick={toggle}
        aria-expanded={open}
        aria-controls="score-breakdown-panel"
      >
        <span className="breakdown-toggle-label">Why this score</span>
        <span className={`breakdown-chevron ${open ? 'breakdown-chevron--open' : ''}`}>⌄</span>
      </button>

      {open && (
        <div className="breakdown-panel" id="score-breakdown-panel">
          {loading && (
            <div className="breakdown-loading">
              <Spinner size={20} />
            </div>
          )}

          {!loading && error && <p className="breakdown-error">{error}</p>}

          {!loading && !error && categories.length === 0 && (
            <p className="breakdown-empty">No breakdown available yet.</p>
          )}

          {!loading && !error && categories.length > 0 && (
            <>
              <p className="breakdown-intro">
                How each category contributed. We only show your own answers — never theirs.
              </p>
              <div className="breakdown-rows">
                {categories.map(row => {
                  const pct        = normalizeScore(row.score);
                  const color      = getCompatibilityColor(pct);
                  const flagged    = !!row.dealBreakerTriggered;
                  const yourValue  = formatYourValue(row);
                  return (
                    <div
                      key={row.key}
                      className={`breakdown-row ${flagged ? 'breakdown-row--dealbreaker' : ''}`}
                    >
                      <div className="breakdown-row-head">
                        <span className="breakdown-row-label">{row.label || row.key}</span>
                        <div className="breakdown-row-badges">
                          {row.isDealBreaker && (
                            <span className={`breakdown-db-badge ${flagged ? 'breakdown-db-badge--triggered' : ''}`}>
                              {flagged ? 'Deal-breaker hit' : 'Deal-breaker'}
                            </span>
                          )}
                          <span className="breakdown-row-pct">{Math.round(pct * 100)}%</span>
                        </div>
                      </div>

                      <div className="breakdown-bar-track">
                        <div
                          className="breakdown-bar-fill"
                          style={{ width: `${Math.round(pct * 100)}%`, backgroundColor: flagged ? 'var(--color-danger)' : color }}
                        />
                      </div>

                      <p className="breakdown-row-sentence">{breakdownSentence(row)}</p>

                      <div className="breakdown-row-meta">
                        {yourValue && <span className="breakdown-your-value">You: {yourValue}</span>}
                        {row.difference && DIFFERENCE_LABEL[row.difference] && (
                          <span className={`breakdown-diff-chip breakdown-diff-chip--${row.difference}`}>
                            {DIFFERENCE_LABEL[row.difference]}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
