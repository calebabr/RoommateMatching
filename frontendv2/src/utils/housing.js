// Housing intent options (P3FT.10)
// Values sent to the API are the lowercase literals the backend validates against.

export const HOUSING_TYPE_OPTIONS = [
  { value: 'on-campus',  label: 'On campus',        emoji: '🏫' },
  { value: 'off-campus', label: 'Off campus',       emoji: '🏢' },
  { value: 'either',     label: 'Either works',     emoji: '🤷' },
];

export const LEASE_TERM_OPTIONS = [
  { value: 'fall',      label: 'Fall semester'   },
  { value: 'spring',    label: 'Spring semester' },
  { value: 'summer',    label: 'Summer'          },
  { value: 'full-year', label: 'Full year'       },
];

export const MOVE_IN_SEASONS = ['Spring', 'Summer', 'Fall'];
export const MOVE_IN_YEARS   = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035];

export const PREFERRED_LOCATION_MAX = 60;
export const BUDGET_MIN = 0;
export const BUDGET_MAX = 5000;

export const housingTypeLabel = (value) =>
  HOUSING_TYPE_OPTIONS.find(o => o.value === value)?.label || '';

export const leaseTermLabel = (value) =>
  LEASE_TERM_OPTIONS.find(o => o.value === value)?.label || '';

/** Budget is only meaningful for users open to off-campus housing. */
export const showsBudget = (housingType) =>
  housingType === 'off-campus' || housingType === 'either';

export const formatBudget = (min, max) => {
  const hasMin = min !== null && min !== undefined && min !== '';
  const hasMax = max !== null && max !== undefined && max !== '';
  if (hasMin && hasMax) return `$${min}–$${max}/mo`;
  if (hasMax)           return `Up to $${max}/mo`;
  if (hasMin)           return `From $${min}/mo`;
  return '';
};

/**
 * Build the housing portion of an update/create payload from form state.
 * Empty values are sent as `undefined` so they are omitted from the request.
 */
export const buildHousingPayload = ({
  housingType, preferredLocation, budgetMin, budgetMax, leaseTerm, moveInSeason, moveInYear,
}) => {
  const offCampus = showsBudget(housingType);
  return {
    housingType:       housingType || undefined,
    preferredLocation: preferredLocation?.trim() ? preferredLocation.trim().slice(0, PREFERRED_LOCATION_MAX) : undefined,
    budgetMin:         offCampus && budgetMin !== '' && budgetMin !== null && budgetMin !== undefined ? parseInt(budgetMin, 10) : undefined,
    budgetMax:         offCampus && budgetMax !== '' && budgetMax !== null && budgetMax !== undefined ? parseInt(budgetMax, 10) : undefined,
    leaseTerm:         leaseTerm || undefined,
    moveInSeason:      moveInSeason || undefined,
    moveInYear:        moveInYear ? parseInt(moveInYear, 10) : undefined,
  };
};

/** True when a profile has any housing intent worth displaying. */
export const hasHousingInfo = (u) =>
  !!(u?.housingType || u?.preferredLocation || u?.leaseTerm ||
     (u?.moveInSeason && u?.moveInYear) ||
     u?.budgetMin != null || u?.budgetMax != null);
