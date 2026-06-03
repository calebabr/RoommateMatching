import React from 'react';
import { Colors } from '../utils/theme';

export default function SliderPicker({ min, max, value, onChange, formatLabel }) {
  const pct = ((value - min) / (max - min)) * 100;
  // The track background gradient is dynamic (depends on the slider value),
  // so it must remain inline.
  const trackStyle = {
    background: `linear-gradient(to right, ${Colors.accent} ${pct}%, ${Colors.border} ${pct}%)`,
  };

  return (
    <div className="slider-wrapper">
      <div className="slider-label-row">
        <span className="slider-value-label">
          {formatLabel ? formatLabel(value) : value}
        </span>
      </div>
      <input
        className="slider-range"
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(parseInt(e.target.value, 10))}
        style={trackStyle}
      />
      <div className="slider-minmax-row">
        <span className="slider-min-label">{min}</span>
        <span className="slider-max-label">{max}</span>
      </div>
    </div>
  );
}
