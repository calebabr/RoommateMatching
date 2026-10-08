import { describe, it, expect, beforeEach } from 'vitest';
import {
  EMPTY_FILTERS,
  FILTER_LIMITS,
  FILTER_STORAGE_KEY,
  activeFilterKeys,
  buildFilterParams,
  countActiveFilters,
  filterChips,
  loadFilters,
  normalizeFilters,
  saveFilters,
} from './discoverFilters';

const f = (overrides) => ({ ...EMPTY_FILTERS, ...overrides });

/** The query string axios would actually put on the wire. */
const qs = (filters) => {
  const params = buildFilterParams(filters);
  return params ? params.toString() : undefined;
};

describe('buildFilterParams — repeatable params', () => {
  it('returns undefined when nothing is set, so an unfiltered call is unchanged', () => {
    expect(buildFilterParams(EMPTY_FILTERS)).toBeUndefined();
    expect(buildFilterParams(undefined)).toBeUndefined();
    expect(buildFilterParams(null)).toBeUndefined();
    expect(buildFilterParams({})).toBeUndefined();
  });

  it('emits tags once per value rather than comma-joining them', () => {
    const params = buildFilterParams(f({ tags: ['Night Owl', 'Fitness'] }));
    expect(params.getAll('tags')).toEqual(['Night Owl', 'Fitness']);
  });

  it('never produces a comma-joined tags value', () => {
    // A comma-joined string is one literal tag to the backend and 422s, so this
    // is the specific regression worth pinning.
    const query = qs(f({ tags: ['Night Owl', 'Fitness'] }));
    expect(query).toBe('tags=Night+Owl&tags=Fitness');
    expect(query).not.toContain('%2C');
  });

  it('emits major once per value', () => {
    const params = buildFilterParams(f({ major: ['Engineering', 'Nursing'] }));
    expect(params.getAll('major')).toEqual(['Engineering', 'Nursing']);
    expect(qs(f({ major: ['A', 'B'] }))).toBe('major=A&major=B');
  });

  it('serializes a single repeatable value without a trailing separator', () => {
    expect(qs(f({ tags: ['Gaming'] }))).toBe('tags=Gaming');
  });

  it('carries scalar filters through unchanged', () => {
    const params = buildFilterParams(f({ religion: 'Christian', housingType: 'on-campus' }));
    expect(params.get('religion')).toBe('Christian');
    expect(params.get('housingType')).toBe('on-campus');
  });

  it('omits keys that are not set', () => {
    const params = buildFilterParams(f({ religion: 'Christian' }));
    expect([...params.keys()]).toEqual(['religion']);
  });
});

describe('buildFilterParams — clamping and caps', () => {
  it('caps tags at 10', () => {
    const tags = Array.from({ length: 14 }, (_, i) => `t${i}`);
    expect(buildFilterParams(f({ tags })).getAll('tags')).toHaveLength(FILTER_LIMITS.tags);
  });

  it('caps major at 20', () => {
    const major = Array.from({ length: 25 }, (_, i) => `m${i}`);
    expect(buildFilterParams(f({ major })).getAll('major')).toHaveLength(FILTER_LIMITS.major);
  });

  it('keeps exactly the cap when the cap is hit', () => {
    const tags = Array.from({ length: 10 }, (_, i) => `t${i}`);
    expect(buildFilterParams(f({ tags })).getAll('tags')).toHaveLength(10);
  });

  it('clamps budgetMax down to 5000', () => {
    expect(buildFilterParams(f({ budgetMax: '99999' })).get('budgetMax')).toBe('5000');
  });

  it('clamps a negative budgetMax up to 0', () => {
    expect(buildFilterParams(f({ budgetMax: '-50' })).get('budgetMax')).toBe('0');
  });

  it('keeps budgetMax 0, which is a real filter and not an empty value', () => {
    expect(buildFilterParams(f({ budgetMax: '0' })).get('budgetMax')).toBe('0');
  });

  it('clamps minScore into 0-100', () => {
    expect(buildFilterParams(f({ minScore: '250' })).get('minScore')).toBe('100');
    expect(buildFilterParams(f({ minScore: '-7' })).get('minScore')).toBe('0');
  });

  it('drops a non-numeric budgetMax rather than sending garbage', () => {
    expect(buildFilterParams(f({ budgetMax: 'abc' }))).toBeUndefined();
  });
});

describe('buildFilterParams — graduation-year range', () => {
  it('sends both bounds when the range is valid', () => {
    const params = buildFilterParams(f({ gradYearMin: '2026', gradYearMax: '2028' }));
    expect(params.get('gradYearMin')).toBe('2026');
    expect(params.get('gradYearMax')).toBe('2028');
  });

  it('sends a lone lower bound', () => {
    expect(qs(f({ gradYearMin: '2026' }))).toBe('gradYearMin=2026');
  });

  it('sends a lone upper bound', () => {
    expect(qs(f({ gradYearMax: '2026' }))).toBe('gradYearMax=2026');
  });

  it('allows an equal min and max', () => {
    const params = buildFilterParams(f({ gradYearMin: '2026', gradYearMax: '2026' }));
    expect(params.get('gradYearMin')).toBe('2026');
  });

  it('drops an inverted range entirely instead of sending a guaranteed 422', () => {
    expect(buildFilterParams(f({ gradYearMin: '2028', gradYearMax: '2026' }))).toBeUndefined();
  });

  it('drops only the inverted range, keeping the other filters', () => {
    const params = buildFilterParams(
      f({ gradYearMin: '2028', gradYearMax: '2026', religion: 'Christian' }),
    );
    expect(params.has('gradYearMin')).toBe(false);
    expect(params.has('gradYearMax')).toBe(false);
    expect(params.get('religion')).toBe('Christian');
  });
});

describe('normalizeFilters', () => {
  it('fills in every key from a partial object', () => {
    expect(Object.keys(normalizeFilters({ religion: 'X' })).sort())
      .toEqual(Object.keys(EMPTY_FILTERS).sort());
  });

  it('coerces a non-array major to an empty list', () => {
    expect(normalizeFilters({ major: 'Engineering' }).major).toEqual([]);
  });

  it('drops non-string entries from list filters', () => {
    expect(normalizeFilters({ tags: ['Gaming', 42, null, ''] }).tags).toEqual(['Gaming']);
  });

  it('coerces numbers to strings', () => {
    expect(normalizeFilters({ budgetMax: 900 }).budgetMax).toBe('900');
  });

  it('preserves a zero rather than treating it as unset', () => {
    expect(normalizeFilters({ budgetMax: 0 }).budgetMax).toBe('0');
  });

  it('turns null and undefined into empty strings', () => {
    expect(normalizeFilters({ religion: null }).religion).toBe('');
    expect(normalizeFilters(undefined).religion).toBe('');
  });
});

describe('active filter introspection', () => {
  it('reports no active filters for the empty state', () => {
    expect(countActiveFilters(EMPTY_FILTERS)).toBe(0);
    expect(activeFilterKeys(EMPTY_FILTERS)).toEqual([]);
  });

  it('counts an empty array as inactive', () => {
    expect(countActiveFilters(f({ tags: [] }))).toBe(0);
  });

  it('counts each set key once', () => {
    expect(countActiveFilters(f({ tags: ['a', 'b'], religion: 'X' }))).toBe(2);
  });

  it('returns KEYS only — values are sensitive and must not reach analytics', () => {
    const keys = activeFilterKeys(f({ religion: 'Christian', budgetMax: '900' }));
    expect(keys).toEqual(['religion', 'budgetMax']);
    expect(JSON.stringify(keys)).not.toContain('Christian');
    expect(JSON.stringify(keys)).not.toContain('900');
  });
});

describe('persistence', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips filters for a user', () => {
    saveFilters(7, f({ tags: ['Gaming'], religion: 'Christian' }));
    expect(loadFilters(7)).toMatchObject({ tags: ['Gaming'], religion: 'Christian' });
  });

  it('keeps each user separate', () => {
    saveFilters(1, f({ religion: 'A' }));
    saveFilters(2, f({ religion: 'B' }));
    expect(loadFilters(1).religion).toBe('A');
    expect(loadFilters(2).religion).toBe('B');
  });

  it('returns the empty state for an unknown user', () => {
    expect(loadFilters(999)).toEqual(EMPTY_FILTERS);
  });

  it('returns the empty state when no user id is supplied', () => {
    expect(loadFilters(undefined)).toEqual(EMPTY_FILTERS);
    expect(loadFilters(null)).toEqual(EMPTY_FILTERS);
  });

  it('removes the entry entirely when filters are cleared', () => {
    saveFilters(7, f({ religion: 'Christian' }));
    saveFilters(7, EMPTY_FILTERS);
    expect(JSON.parse(localStorage.getItem(FILTER_STORAGE_KEY))['7']).toBeUndefined();
  });

  it('survives corrupt stored JSON', () => {
    localStorage.setItem(FILTER_STORAGE_KEY, 'not json{');
    expect(loadFilters(7)).toEqual(EMPTY_FILTERS);
  });

  it('never writes filters to the URL', () => {
    saveFilters(7, f({ religion: 'Christian', budgetMax: '900' }));
    expect(window.location.search).toBe('');
  });
});

describe('filterChips', () => {
  it('emits one chip per major and per tag', () => {
    const chips = filterChips(f({ major: ['A', 'B'], tags: ['Gaming'] }));
    expect(chips.map(c => c.id)).toEqual(['major:A', 'major:B', 'tag:Gaming']);
  });

  it("a chip's patch removes just that value", () => {
    const chips = filterChips(f({ tags: ['Gaming', 'Fitness'] }));
    expect(chips[0].patch).toEqual({ tags: ['Fitness'] });
  });

  it('collapses the grad-year range into a single chip', () => {
    const chips = filterChips(f({ gradYearMin: '2026', gradYearMax: '2028' }));
    expect(chips).toHaveLength(1);
    expect(chips[0].label).toBe('Grads 2026–2028');
    expect(chips[0].patch).toEqual({ gradYearMin: '', gradYearMax: '' });
  });

  it('labels a single-year range without a dash', () => {
    expect(filterChips(f({ gradYearMin: '2026', gradYearMax: '2026' }))[0].label)
      .toBe('Grads 2026');
  });

  it('labels open-ended ranges', () => {
    expect(filterChips(f({ gradYearMin: '2026' }))[0].label).toBe('Grads 2026+');
    expect(filterChips(f({ gradYearMax: '2026' }))[0].label).toBe('Grads up to 2026');
  });

  it('shows a budget chip for 0', () => {
    const chip = filterChips(f({ budgetMax: '0' })).find(c => c.id === 'budgetMax');
    expect(chip.label).toBe('Up to $0/mo');
  });

  it('produces no chips for the empty state', () => {
    expect(filterChips(EMPTY_FILTERS)).toEqual([]);
    expect(filterChips(undefined)).toEqual([]);
  });
});
