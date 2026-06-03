import React from 'react';
import { Colors } from '../utils/theme';

export default function Toggle({ value, onChange }) {
  return (
    <div
      className="toggle-track"
      onClick={() => onChange(!value)}
      style={{ backgroundColor: value ? Colors.danger : Colors.border }}
    >
      <div
        className="toggle-thumb"
        style={{ left: value ? 22 : 2 }}
      />
    </div>
  );
}
