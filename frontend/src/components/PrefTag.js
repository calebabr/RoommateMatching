import React from 'react';
import { View, Text } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { COLORS } from '../constants/theme';

export default function PrefTag({ icon, label, isDealBreaker = false }) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        backgroundColor: isDealBreaker ? 'rgba(232,90,90,0.12)' : COLORS.surfaceAlt,
        borderWidth: 1,
        borderColor: isDealBreaker ? 'rgba(232,90,90,0.3)' : COLORS.border,
        borderRadius: 20,
        paddingVertical: 6,
        paddingHorizontal: 12,
      }}
    >
      <Feather name={icon} size={12} color={isDealBreaker ? COLORS.red : COLORS.accent} />
      <Text style={{ color: isDealBreaker ? COLORS.red : COLORS.text, fontSize: 12, fontWeight: '600' }}>
        {label}
      </Text>
    </View>
  );
}
