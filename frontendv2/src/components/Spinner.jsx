import React from 'react';
import { Colors } from '../utils/theme';

export default function Spinner({ size = 32, color = Colors.accent }) {
  return (
    <div
      className="spinner"
      style={{
        width: size,
        height: size,
        borderTopColor: color,
      }}
    />
  );
}
