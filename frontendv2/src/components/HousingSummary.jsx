import React from 'react';
import { housingTypeLabel, leaseTermLabel, formatBudget, hasHousingInfo, showsBudget } from '../utils/housing';

/**
 * Read-only housing intent display (P3FT.10), used on ProfilePage and UserDetailPage.
 * Renders nothing when the profile has no housing information.
 */
export default function HousingSummary({ profile, title = 'Housing' }) {
  if (!hasHousingInfo(profile)) return null;

  const budget = showsBudget(profile.housingType)
    ? formatBudget(profile.budgetMin, profile.budgetMax)
    : '';

  const rows = [
    profile.housingType      && { key: 'type',     label: 'Looking for', value: housingTypeLabel(profile.housingType) },
    profile.preferredLocation&& { key: 'location', label: 'Prefers',     value: profile.preferredLocation },
    budget                   && { key: 'budget',   label: 'Budget',      value: budget },
    profile.leaseTerm        && { key: 'lease',    label: 'Lease',       value: leaseTermLabel(profile.leaseTerm) },
    (profile.moveInSeason && profile.moveInYear)
                             && { key: 'movein',   label: 'Move-in',     value: `${profile.moveInSeason} ${profile.moveInYear}` },
  ].filter(Boolean);

  if (rows.length === 0) return null;

  return (
    <div className="housing-summary">
      <p className="housing-summary-title">{title}</p>
      <div className="housing-summary-rows">
        {rows.map(r => (
          <div key={r.key} className="housing-summary-row">
            <span className="housing-summary-label">{r.label}</span>
            <span className="housing-summary-value">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
