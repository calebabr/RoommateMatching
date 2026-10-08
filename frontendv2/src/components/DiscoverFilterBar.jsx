import React, { useEffect, useState } from 'react';
import {
  EMPTY_FILTERS,
  FILTER_OPTIONS,
  FILTER_LIMITS,
  MIN_SCORE_MIN,
  MIN_SCORE_MAX,
  countActiveFilters,
  filterChips,
} from '../utils/discoverFilters';

/**
 * P3FT.16 — Discover filter bar.
 *
 * The bar itself shows the "Filters" trigger, the active-filter chips, a
 * "Clear all", and the result count. The controls live in a modal that renders
 * as a centred dialog on desktop and a bottom sheet on mobile (via the shared
 * `.overlay-bg--sheet` modifier).
 *
 * `onChange(nextFilters)` is called only when the user actually applies or
 * clears something — the parent owns persistence and analytics.
 */
export default function DiscoverFilterBar({ filters, onChange, resultCount, filteredOut, loading }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(filters);

  // Re-seed the draft whenever the sheet opens or the applied filters change.
  useEffect(() => { if (open) setDraft(filters); }, [open, filters]);

  const activeCount = countActiveFilters(filters);
  const chips = filterChips(filters);

  const setDraftField = (patch) => setDraft(prev => ({ ...prev, ...patch }));

  // The backend caps `major` at 20 and `tags` at 10 and 422s past that, so the
  // selection is capped here rather than failing the whole request later.
  const toggleInList = (key, value) => setDraft(prev => {
    const list = prev[key] || [];
    if (list.includes(value)) return { ...prev, [key]: list.filter(v => v !== value) };
    if (list.length >= FILTER_LIMITS[key]) return prev;
    return { ...prev, [key]: [...list, value] };
  });

  const atLimit = (key) => (draft[key] || []).length >= FILTER_LIMITS[key];

  const apply = () => { onChange(draft); setOpen(false); };
  const clearAll = () => { onChange({ ...EMPTY_FILTERS }); setDraft({ ...EMPTY_FILTERS }); setOpen(false); };

  const gradYearInvalid =
    draft.gradYearMin !== '' && draft.gradYearMax !== '' &&
    Number(draft.gradYearMin) > Number(draft.gradYearMax);

  return (
    <>
      <div className="discover-filter-bar">
        <button
          type="button"
          className={`discover-filter-trigger ${activeCount > 0 ? 'discover-filter-trigger--active' : ''}`}
          onClick={() => setOpen(true)}
        >
          <span aria-hidden="true">⚙</span> Filters
          {activeCount > 0 && <span className="discover-filter-count">{activeCount}</span>}
        </button>

        {chips.length > 0 && (
          <div className="discover-filter-chips">
            {chips.map(chip => (
              <button
                key={chip.id}
                type="button"
                className="discover-filter-chip"
                onClick={() => onChange({ ...filters, ...chip.patch })}
                aria-label={`Remove filter ${chip.label}`}
              >
                {chip.label} <span aria-hidden="true">✕</span>
              </button>
            ))}
            <button type="button" className="discover-filter-clear" onClick={clearAll}>
              Clear all
            </button>
          </div>
        )}

        <span className="discover-filter-result-count">
          {loading
            ? 'Loading…'
            : `${resultCount} ${resultCount === 1 ? 'result' : 'results'}${
                activeCount > 0 && filteredOut > 0 ? ` · ${filteredOut} filtered out` : ''
              }`}
        </span>
      </div>

      {open && (
        <div className="overlay-bg overlay-bg--sheet" onClick={() => setOpen(false)}>
          <div
            className="inline-modal discover-filter-sheet"
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Discover filters"
          >
            <div className="discover-filter-sheet-head">
              <p className="discover-filter-sheet-title">Filters</p>
              <button
                type="button"
                className="discover-filter-sheet-close"
                onClick={() => setOpen(false)}
                aria-label="Close filters"
              >✕</button>
            </div>

            <div className="discover-filter-sheet-body">
              {/* Major */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">
                  Major
                  {atLimit('major') && (
                    <span className="discover-filter-value">Max {FILTER_LIMITS.major}</span>
                  )}
                </p>
                <div className="discover-filter-optionlist">
                  {FILTER_OPTIONS.major.map(m => {
                    const selected = (draft.major || []).includes(m);
                    return (
                      <button
                        key={m}
                        type="button"
                        className={`discover-filter-option ${selected ? 'discover-filter-option--selected' : ''}`}
                        onClick={() => toggleInList('major', m)}
                        disabled={!selected && atLimit('major')}
                        aria-pressed={selected}
                      >
                        {m}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Graduation year range */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">Graduation year</p>
                <div className="discover-filter-row">
                  <select
                    className="form-input"
                    value={draft.gradYearMin}
                    onChange={e => setDraftField({ gradYearMin: e.target.value })}
                    aria-label="Earliest graduation year"
                  >
                    <option value="">From</option>
                    {FILTER_OPTIONS.gradYears.map(y => <option key={y} value={y}>{y}</option>)}
                  </select>
                  <span className="discover-filter-row-sep">to</span>
                  <select
                    className="form-input"
                    value={draft.gradYearMax}
                    onChange={e => setDraftField({ gradYearMax: e.target.value })}
                    aria-label="Latest graduation year"
                  >
                    <option value="">To</option>
                    {FILTER_OPTIONS.gradYears.map(y => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
                {gradYearInvalid && (
                  <p className="discover-filter-error">Your earliest year is after your latest year.</p>
                )}
              </div>

              {/* Lifestyle tags */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">
                  Lifestyle tags
                  {atLimit('tags') && (
                    <span className="discover-filter-value">Max {FILTER_LIMITS.tags}</span>
                  )}
                </p>
                <div className="discover-filter-optionlist">
                  {FILTER_OPTIONS.tags.map(t => {
                    const selected = (draft.tags || []).includes(t);
                    return (
                      <button
                        key={t}
                        type="button"
                        className={`discover-filter-option ${selected ? 'discover-filter-option--selected' : ''}`}
                        onClick={() => toggleInList('tags', t)}
                        disabled={!selected && atLimit('tags')}
                        aria-pressed={selected}
                      >
                        {t}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Religion */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">Religion</p>
                <select
                  className="form-input"
                  value={draft.religion}
                  onChange={e => setDraftField({ religion: e.target.value })}
                  aria-label="Religion"
                >
                  <option value="">Any</option>
                  {FILTER_OPTIONS.religion.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>

              {/* Housing type */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">Housing</p>
                <div className="discover-filter-optionlist">
                  {FILTER_OPTIONS.housingType.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      className={`discover-filter-option ${draft.housingType === opt.value ? 'discover-filter-option--selected' : ''}`}
                      onClick={() => setDraftField({ housingType: draft.housingType === opt.value ? '' : opt.value })}
                      aria-pressed={draft.housingType === opt.value}
                    >
                      {opt.emoji} {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Budget */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">Max monthly budget</p>
                <input
                  className="form-input"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={FILTER_OPTIONS.budgetMax}
                  placeholder={`Any (up to $${FILTER_OPTIONS.budgetMax})`}
                  value={draft.budgetMax}
                  onChange={e => setDraftField({ budgetMax: e.target.value })}
                  // The backend bounds this 0–5000; clamp on blur so a typed
                  // out-of-range value can never 422 the whole request.
                  onBlur={e => {
                    const raw = e.target.value;
                    if (raw === '') return;
                    const n = parseInt(raw, 10);
                    setDraftField({
                      budgetMax: Number.isNaN(n)
                        ? ''
                        : String(Math.min(Math.max(n, 0), FILTER_LIMITS.budgetMax)),
                    });
                  }}
                  aria-label="Maximum monthly budget in dollars"
                />
              </div>

              {/* Minimum score */}
              <div className="discover-filter-group">
                <p className="discover-filter-label">
                  Minimum compatibility
                  <span className="discover-filter-value">
                    {draft.minScore === '' ? 'Any' : `${draft.minScore}%`}
                  </span>
                </p>
                <input
                  type="range"
                  className="discover-filter-range"
                  min={MIN_SCORE_MIN}
                  max={MIN_SCORE_MAX}
                  step={5}
                  value={draft.minScore === '' ? MIN_SCORE_MIN : draft.minScore}
                  onChange={e => setDraftField({ minScore: e.target.value === '0' ? '' : e.target.value })}
                  aria-label="Minimum compatibility score"
                />
              </div>
            </div>

            <div className="discover-filter-sheet-actions">
              <button
                type="button"
                className="discover-filter-apply-btn"
                onClick={apply}
                disabled={gradYearInvalid}
              >
                Show results
              </button>
              <button type="button" className="discover-filter-reset-btn" onClick={clearAll}>
                Clear all
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
