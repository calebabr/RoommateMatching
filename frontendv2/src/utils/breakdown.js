import { CATEGORIES } from './categories';

/**
 * Copy for the "Why this score" panel (P3FT.11).
 *
 * The API deliberately does NOT return the other user's raw preference values —
 * only a bucketed `difference` of "same" | "close" | "different". Every sentence
 * below is therefore written from `difference` plus the viewer's own value.
 */
const PHRASES = {
  sleepScoreWD: {
    same:      'You go to bed around the same time on weekdays',
    close:     'Your weekday bedtimes are within an hour or so',
    different: 'Your weekday bedtimes are several hours apart',
  },
  sleepScoreWE: {
    same:      'Your weekend sleep schedules line up',
    close:     'Your weekend bedtimes are close',
    different: 'Your weekend sleep schedules are quite different',
  },
  cleanlinessScore: {
    same:      'You keep your space about equally tidy',
    close:     'Similar standards for keeping things clean',
    different: 'One of you is noticeably tidier than the other',
  },
  noiseToleranceScore: {
    same:      'You both want the same noise level at home',
    close:     'Similar tolerance for noise',
    different: 'One of you wants a quieter room than the other',
  },
  guestsScore: {
    same:      'You expect guests over about as often',
    close:     'Similar expectations about having people over',
    different: 'One of you plans on guests much more often',
  },
  personalityScore: {
    same:      'Similar social energy at home',
    close:     'Fairly similar social energy',
    different: 'One of you is much more outgoing at home',
  },
  smokingScore: {
    same:      'You feel the same about smoking and substances',
    close:     'Close on smoking and substances',
    different: 'You feel quite differently about smoking and substances',
  },
  sharedSpaceScore: {
    same:      'You share common areas and belongings the same way',
    close:     'Similar boundaries around shared space',
    different: 'One of you wants more privacy with shared space',
  },
  communicationScore: {
    same:      'You handle roommate issues the same way',
    close:     'Similar approach to working out problems',
    different: 'You handle conflict quite differently',
  },
};

const GENERIC = {
  same:      (label) => `You both answered the same on ${label.toLowerCase()}`,
  close:     (label) => `Close answers on ${label.toLowerCase()}`,
  different: (label) => `Your answers on ${label.toLowerCase()} are far apart`,
};

const CATEGORY_BY_KEY = CATEGORIES.reduce((acc, c) => { acc[c.key] = c; return acc; }, {});

/** Per-category scores may arrive as 0–1 or 0–100; normalise to 0–1. */
export const normalizeScore = (score) => {
  const n = Number(score);
  if (!Number.isFinite(n)) return 0;
  const v = n > 1 ? n / 100 : n;
  return Math.max(0, Math.min(1, v));
};

/** Short plain-language sentence for one breakdown row. */
export const breakdownSentence = (row) => {
  const label = row?.label || CATEGORY_BY_KEY[row?.key]?.label || 'this category';
  if (row?.dealBreakerTriggered) {
    return `Deal-breaker — your answers on ${label.toLowerCase()} are too far apart`;
  }
  const diff = row?.difference;
  const phrase = PHRASES[row?.key]?.[diff];
  if (phrase) return phrase;
  if (GENERIC[diff]) return GENERIC[diff](label);
  return `Compared on ${label.toLowerCase()}`;
};

/** "You: 11:00 PM" style caption for the viewer's own answer. */
export const formatYourValue = (row) => {
  if (row?.yourValue === null || row?.yourValue === undefined || row?.yourValue === '') return '';
  const cat = CATEGORY_BY_KEY[row?.key];
  if (cat && typeof row.yourValue === 'number') return cat.formatValue(row.yourValue);
  return String(row.yourValue);
};

export const DIFFERENCE_LABEL = {
  same:      'Same',
  close:     'Close',
  different: 'Different',
};
