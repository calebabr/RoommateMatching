import React from 'react';
import {
  HOUSING_TYPE_OPTIONS,
  LEASE_TERM_OPTIONS,
  MOVE_IN_SEASONS,
  MOVE_IN_YEARS,
  PREFERRED_LOCATION_MAX,
  BUDGET_MIN,
  BUDGET_MAX,
  showsBudget,
} from '../utils/housing';

/**
 * Shared housing-intent editor (P3FT.10) used by SignupPage and ProfilePage.
 *
 * `values` is `{ housingType, preferredLocation, budgetMin, budgetMax, leaseTerm, moveInSeason, moveInYear }`.
 * `onChange(field, value)` is called for every edit.
 * `inputClass` lets each host page reuse its own input styling class.
 */
export default function HousingFields({ values, onChange, inputClass = 'form-input' }) {
  const {
    housingType = '', preferredLocation = '', budgetMin = '', budgetMax = '',
    leaseTerm = '', moveInSeason = '', moveInYear = '',
  } = values || {};

  const budgetVisible = showsBudget(housingType);
  const budgetInvalid =
    budgetMin !== '' && budgetMax !== '' &&
    Number(budgetMin) > Number(budgetMax);

  return (
    <div className="housing-fields">
      <div className="housing-field">
        <label className="housing-field-label">Where do you want to live?</label>
        <div className="housing-type-row">
          {HOUSING_TYPE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange('housingType', housingType === opt.value ? '' : opt.value)}
              className={`housing-type-btn ${housingType === opt.value ? 'housing-type-btn--selected' : ''}`}
              aria-pressed={housingType === opt.value}
            >
              <span className="housing-type-emoji">{opt.emoji}</span>
              <span className="housing-type-label">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="housing-field">
        <label className="housing-field-label" htmlFor="housing-preferred-location">
          Preferred dorm or complex (optional)
        </label>
        <input
          id="housing-preferred-location"
          className={inputClass}
          value={preferredLocation}
          maxLength={PREFERRED_LOCATION_MAX}
          placeholder="e.g. The Quad, South Donahue, 160 Ross"
          onChange={e => onChange('preferredLocation', e.target.value)}
        />
        <p className="housing-char-count">{preferredLocation.length}/{PREFERRED_LOCATION_MAX}</p>
      </div>

      {budgetVisible && (
        <div className="housing-field">
          <label className="housing-field-label">Monthly budget (optional)</label>
          <div className="housing-budget-row">
            <input
              className={inputClass}
              type="number"
              inputMode="numeric"
              min={BUDGET_MIN}
              max={BUDGET_MAX}
              placeholder="Min $"
              value={budgetMin}
              onChange={e => onChange('budgetMin', e.target.value)}
              aria-label="Minimum monthly budget in dollars"
            />
            <span className="housing-budget-sep">to</span>
            <input
              className={inputClass}
              type="number"
              inputMode="numeric"
              min={BUDGET_MIN}
              max={BUDGET_MAX}
              placeholder="Max $"
              value={budgetMax}
              onChange={e => onChange('budgetMax', e.target.value)}
              aria-label="Maximum monthly budget in dollars"
            />
          </div>
          <p className="housing-field-hint">
            Only used for off-campus matching. People whose budget can't overlap yours are hidden.
          </p>
          {budgetInvalid && (
            <p className="housing-field-error">Your minimum is higher than your maximum.</p>
          )}
        </div>
      )}

      <div className="housing-field">
        <label className="housing-field-label" htmlFor="housing-lease-term">Lease term (optional)</label>
        <select
          id="housing-lease-term"
          className={inputClass}
          value={leaseTerm}
          onChange={e => onChange('leaseTerm', e.target.value)}
        >
          <option value="">Select a lease term...</option>
          {LEASE_TERM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <div className="housing-field">
        <label className="housing-field-label">Move-in (optional)</label>
        <div className="housing-movein-row">
          <select
            className={inputClass}
            value={moveInSeason}
            onChange={e => onChange('moveInSeason', e.target.value)}
            aria-label="Move-in season"
          >
            <option value="">Season</option>
            {MOVE_IN_SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            className={inputClass}
            value={moveInYear}
            onChange={e => onChange('moveInYear', e.target.value)}
            aria-label="Move-in year"
          >
            <option value="">Year</option>
            {MOVE_IN_YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}
