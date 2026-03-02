import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { COLORS } from '../constants/theme';

const PALETTE = ['#E8A838', '#5ECE7B', '#E878A0', '#6C8EEF', '#E85A5A', '#A078E8'];

export default function Avatar({ uri, name = '', size = 80 }) {
  if (uri) {
    return (
      <Image
        source={{ uri }}
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth: 2,
          borderColor: COLORS.accent,
        }}
      />
    );
  }

  const initials = name ? name.slice(0, 2).toUpperCase() : '??';
  const bg = PALETTE[name ? name.charCodeAt(0) % PALETTE.length : 0];

  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: bg,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ color: '#fff', fontWeight: '700', fontSize: size * 0.32, letterSpacing: 1 }}>
        {initials}
      </Text>
    </View>
  );
}
