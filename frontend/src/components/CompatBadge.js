import React from 'react';
import { View, Text } from 'react-native';
import { COLORS } from '../constants/theme';

export default function CompatBadge({ score, size = 56 }) {
  const pct = Math.round(score * 100);
  const color = pct >= 75 ? COLORS.green : pct >= 50 ? COLORS.accent : COLORS.red;

  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        borderWidth: 3,
        borderColor: color,
        backgroundColor: COLORS.card,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ fontWeight: '800', fontSize: size * 0.26, color }}>{pct}%</Text>
    </View>
  );
}
