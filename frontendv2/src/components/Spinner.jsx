import React from 'react';
import { Colors } from '../utils/theme';

export default function Spinner({ size = 32, color = Colors.accent }) {
  return (
    <div style={{
      width: size, height: size,
      borderRadius: '50%',
      border: `3px solid ${Colors.border}`,
      borderTopColor: color,
      animation: 'spin 0.75s linear infinite',
      flexShrink: 0,
    }} />
  );
}
