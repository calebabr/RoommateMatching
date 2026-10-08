// P3FT.16 — Discover filters.
//
// Filters are query params on `GET /users/{id}/top-matches`. `major` and `tags`
// are REPEATABLE params (`?tags=A&tags=B`), never comma-joined, so params are
// built with URLSearchParams rather than a plain object.
//
// Filters are persisted per user in localStorage and are deliberately NEVER put
// in the URL — they include religion and budget, which are sensitive.

import { LIFESTYLE_TAGS } from './categories';
import { MAJOR_OPTIONS, RELIGION_OPTIONS, GRADUATION_YEARS } from './profileOptions';
import { HOUSING_TYPE_OPTIONS, housingTypeLabel, BUDGET_MAX } from './housing';

export const FILTER_STORAGE_KEY = 'roommatch_discover_filters';

export const MIN_SCORE_MIN = 0;
export const MIN_SCORE_MAX = 100;

// Mirrors the backend `DiscoverFilters` model. That model sets
// `extra: "forbid"` and per-field bounds, so anything out of range is a hard 422
// rather than a silently ignored param — the UI must not let a user build one.
export const FILTER_LIMITS = Object.freeze({
  major: 20,      // major: Field(max_length=20)
  tags: 10,       // tags:  Field(max_length=10)
  budgetMax: 5000,
});

const clampInt = (value, min, max) => {
  const n = parseInt(value, 10);
  if (Number.isNaN(n)) return '';
  return String(Math.min(Math.max(n, min), max));
};

export const EMPTY_FILTERS = Object.freeze({
  major: [],
  gradYearMin: '',
  gradYearMax: '',
  tags: [],
  religion: '',
  housingType: '',
  budgetMax: '',
  minScore: '',
});

export const FILTER_OPTIONS = {
  major: MAJOR_OPTIONS,
  tags: LIFESTYLE_TAGS,
  religion: RELIGION_OPTIONS,
  housingType: HOUSING_TYPE_OPTIONS,
  gradYears: GRADUATION_YEARS,
  budgetMax: BUDGET_MAX,
};

const asList = (v) => (Array.isArray(v) ? v.filter(x => typeof x === 'string' && x) : []);
const asScalar = (v) => (v === 0 ? '0' : (v == null ? '' : String(v)));

/** Coerce anything read back from storage into the canonical filter shape. */
export const normalizeFilters = (raw) => ({
  ...EMPTY_FILTERS,
  major: asList(raw?.major),
  gradYearMin: asScalar(raw?.gradYearMin),
  gradYearMax: asScalar(raw?.gradYearMax),
  tags: asList(raw?.tags),
  religion: asScalar(raw?.religion),
  housingType: asScalar(raw?.housingType),
  budgetMax: asScalar(raw?.budgetMax),
  minScore: asScalar(raw?.minScore),
});

// ── Persistence (per user, one storage key holding a userId → filters map) ──

const readStore = () => {
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
};

export const loadFilters = (userId) => {
  if (userId == null) return { ...EMPTY_FILTERS };
  return normalizeFilters(readStore()[String(userId)]);
};

export const saveFilters = (userId, filters) => {
  if (userId == null) return;
  try {
    const store = readStore();
    if (countActiveFilters(filters) === 0) delete store[String(userId)];
    else store[String(userId)] = normalizeFilters(filters);
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Storage unavailable (private mode / quota) — filters just won't persist.
  }
};

// ── Active-filter introspection ────────────────────────────────────────────

const isSet = (v) => (Array.isArray(v) ? v.length > 0 : v !== '' && v != null);

/** Filter KEYS only — this is what goes to analytics. Never filter values. */
export const activeFilterKeys = (filters) =>
  Object.keys(EMPTY_FILTERS).filter(k => isSet(filters?.[k]));

export const countActiveFilters = (filters) => activeFilterKeys(filters).length;

/**
 * Chips for the filter bar. Each chip carries the `patch` that removes it,
 * so the bar does not need per-key removal logic.
 */
export const filterChips = (filters) => {
  const chips = [];
  const f = filters || EMPTY_FILTERS;

  (f.major || []).forEach(m =>
    chips.push({ id: `major:${m}`, label: m, patch: { major: f.major.filter(x => x !== m) } }));

  (f.tags || []).forEach(t =>
    chips.push({ id: `tag:${t}`, label: t, patch: { tags: f.tags.filter(x => x !== t) } }));

  if (f.gradYearMin || f.gradYearMax) {
    const label = f.gradYearMin && f.gradYearMax
      ? (f.gradYearMin === f.gradYearMax ? `Grads ${f.gradYearMin}` : `Grads ${f.gradYearMin}–${f.gradYearMax}`)
      : f.gradYearMin ? `Grads ${f.gradYearMin}+` : `Grads up to ${f.gradYearMax}`;
    chips.push({ id: 'gradYear', label, patch: { gradYearMin: '', gradYearMax: '' } });
  }

  if (f.religion) chips.push({ id: 'religion', label: f.religion, patch: { religion: '' } });

  if (f.housingType) {
    chips.push({
      id: 'housingType',
      label: housingTypeLabel(f.housingType) || f.housingType,
      patch: { housingType: '' },
    });
  }

  if (f.budgetMax !== '') chips.push({ id: 'budgetMax', label: `Up to $${f.budgetMax}/mo`, patch: { budgetMax: '' } });

  if (f.minScore !== '') chips.push({ id: 'minScore', label: `${f.minScore}%+ match`, patch: { minScore: '' } });

  return chips;
};

// ── Query-param serialization ──────────────────────────────────────────────

/**
 * Build the query params for `GET /users/{id}/top-matches`.
 * Repeatable params are appended once per value: `?tags=A&tags=B`.
 * Returns `undefined` when no filter is set, so an unfiltered call is byte-for-byte
 * what it was before this feature shipped.
 */
export const buildFilterParams = (filters) => {
  const f = normalizeFilters(filters);
  const params = new URLSearchParams();

  // Slicing and clamping here is defence in depth: the sheet already enforces
  // the caps, but a stale localStorage payload must not produce a 422 either.
  f.major.slice(0, FILTER_LIMITS.major).forEach(m => params.append('major', m));
  f.tags.slice(0, FILTER_LIMITS.tags).forEach(t => params.append('tags', t));

  // The backend rejects gradYearMin > gradYearMax outright; drop the range
  // rather than send a request that can only 422.
  const inverted =
    f.gradYearMin !== '' && f.gradYearMax !== '' &&
    Number(f.gradYearMin) > Number(f.gradYearMax);
  if (!inverted) {
    if (f.gradYearMin !== '') params.append('gradYearMin', f.gradYearMin);
    if (f.gradYearMax !== '') params.append('gradYearMax', f.gradYearMax);
  }

  if (f.religion !== '') params.append('religion', f.religion);
  if (f.housingType !== '') params.append('housingType', f.housingType);
  if (f.budgetMax !== '') {
    const budget = clampInt(f.budgetMax, 0, FILTER_LIMITS.budgetMax);
    if (budget !== '') params.append('budgetMax', budget);
  }
  if (f.minScore !== '') {
    const score = clampInt(f.minScore, MIN_SCORE_MIN, MIN_SCORE_MAX);
    if (score !== '') params.append('minScore', score);
  }

  return [...params.keys()].length ? params : undefined;
};
