// Human-readable labels for the 5 preference categories
export const CATEGORIES = [
  {
    key: 'sleepScoreWD',
    label: 'Sleep Schedule (Weekdays)',
    description: 'What time do you go to bed on weekdays?',
    min: 0,
    max: 24,
    unit: ':00',
    formatValue: (v) => {
      const h = Math.round(v) % 24;
      const ampm = h >= 12 ? 'PM' : 'AM';
      const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
      return `${h12}:00 ${ampm}`;
    },
  },
  {
    key: 'sleepScoreWE',
    label: 'Sleep Schedule (Weekends)',
    description: 'What time do you go to bed on weekends?',
    min: 0,
    max: 24,
    unit: ':00',
    formatValue: (v) => {
      const h = Math.round(v) % 24;
      const ampm = h >= 12 ? 'PM' : 'AM';
      const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
      return `${h12}:00 ${ampm}`;
    },
  },
  {
    key: 'cleanlinessScore',
    label: 'Cleanliness',
    description: 'How tidy do you keep your space?',
    min: 0,
    max: 10,
    unit: '/10',
    formatValue: (v) => {
      if (v <= 2) return `${Math.round(v)} — Relaxed`;
      if (v <= 5) return `${Math.round(v)} — Moderate`;
      if (v <= 8) return `${Math.round(v)} — Tidy`;
      return `${Math.round(v)} — Spotless`;
    },
  },
  {
    key: 'noiseToleranceScore',
    label: 'Noise Tolerance',
    description: 'How much noise are you comfortable with?',
    min: 0,
    max: 10,
    unit: '/10',
    formatValue: (v) => {
      if (v <= 2) return `${Math.round(v)} — Very Quiet`;
      if (v <= 5) return `${Math.round(v)} — Moderate`;
      if (v <= 8) return `${Math.round(v)} — Lively`;
      return `${Math.round(v)} — Party Mode`;
    },
  },
  {
    key: 'guestsScore',
    label: 'Guests',
    description: 'How often will you have guests over?',
    min: 0,
    max: 10,
    unit: '/10',
    formatValue: (v) => {
      if (v <= 2) return `${Math.round(v)} — Rarely`;
      if (v <= 5) return `${Math.round(v)} — Sometimes`;
      if (v <= 8) return `${Math.round(v)} — Often`;
      return `${Math.round(v)} — Always`;
    },
  },
];

export const getCompatibilityColor = (score) => {
  if (score >= 0.85) return '#4ADE80';
  if (score >= 0.7) return '#E8A838';
  if (score >= 0.5) return '#FB923C';
  return '#F87171';
};

export const getCompatibilityLabel = (score) => {
  if (score >= 0.85) return 'Excellent';
  if (score >= 0.7) return 'Great';
  if (score >= 0.5) return 'Good';
  return 'Fair';
};
