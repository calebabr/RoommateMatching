import React from 'react';
import { Colors } from '../utils/theme';

export default function SliderPicker({ min, max, value, onChange, formatLabel }) {
  const pct = ((value - min) / (max - min)) * 100;
  const trackStyle = {
    background: `linear-gradient(to right, ${Colors.accent} ${pct}%, ${Colors.border} ${pct}%)`,
  };

  return (
    <div style={{ marginTop: 4 }}>
      <div style={{ textAlign: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: Colors.accent }}>
          {formatLabel ? formatLabel(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(parseInt(e.target.value, 10))}
        style={trackStyle}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <span style={{ fontSize: 11, color: Colors.textMuted }}>{min}</span>
        <span style={{ fontSize: 11, color: Colors.textMuted }}>{max}</span>
      </div>
    </div>
  );
}
