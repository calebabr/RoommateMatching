export const COLORS = {
  bg: '#0E0F13',
  surface: '#17181E',
  surfaceAlt: '#1E2028',
  card: '#1C1D24',
  accent: '#E8A838',
  accentGlow: 'rgba(232,168,56,0.25)',
  accentSoft: '#F5D590',
  green: '#5ECE7B',
  red: '#E85A5A',
  pink: '#E878A0',
  blue: '#6C8EEF',
  text: '#F0EDE6',
  textDim: '#8A8B93',
  textMuted: '#55565E',
  border: '#2A2B33',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const RADIUS = {
  sm: 10,
  md: 16,
  lg: 24,
  full: 999,
};

export const PREFERENCE_CONFIG = {
  sleepScoreWD: {
    label: 'Sleep Time (Weekdays)',
    description: 'Military time: 0=midnight, 12=noon, 22=10PM',
    icon: 'moon',
    min: 0,
    max: 24,
    unit: ':00',
  },
  sleepScoreWE: {
    label: 'Sleep Time (Weekends)',
    description: 'Military time: when you typically go to bed',
    icon: 'moon',
    min: 0,
    max: 24,
    unit: ':00',
  },
  cleanlinessScore: {
    label: 'Cleanliness',
    description: '0 = carefree, 10 = spotless',
    icon: 'star',
    min: 0,
    max: 10,
    unit: '/10',
  },
  noiseToleranceScore: {
    label: 'Noise Tolerance',
    description: '0 = total quiet, 10 = bring the noise',
    icon: 'volume-2',
    min: 0,
    max: 10,
    unit: '/10',
  },
  guestsScore: {
    label: 'Guests',
    description: '0 = no guests, 10 = always hosting',
    icon: 'users',
    min: 0,
    max: 10,
    unit: '/10',
  },
};
