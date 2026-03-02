import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Feather } from '@expo/vector-icons';
import Slider from './Slider';
import { COLORS } from '../constants/theme';

export default function PreferenceSlider({
  label,
  description,
  icon,
  value,
  min = 0,
  max = 10,
  isDealBreaker = false,
  onValueChange,
  onDealBreakerChange,
}) {
  return (
    <View style={styles.wrap}>
      <View style={styles.header}>
        <View style={styles.labelRow}>
          {icon && <Feather name={icon} size={16} color={COLORS.accent} />}
          <Text style={styles.label}>{label}</Text>
        </View>
        <Text style={styles.val}>{value}</Text>
      </View>

      {description && <Text style={styles.desc}>{description}</Text>}

      <Slider value={value} min={min} max={max} onValueChange={onValueChange} />

      <View style={styles.rangeRow}>
        <Text style={styles.rangeText}>{min}</Text>
        <Text style={styles.rangeText}>{max}</Text>
      </View>

      <TouchableOpacity
        style={styles.dbRow}
        onPress={() => onDealBreakerChange(!isDealBreaker)}
        activeOpacity={0.7}
      >
        <View style={[styles.checkbox, isDealBreaker && styles.checkboxOn]}>
          {isDealBreaker && <Feather name="check" size={12} color="#fff" />}
        </View>
        <Text style={[styles.dbText, isDealBreaker && { color: COLORS.red }]}>
          Dealbreaker
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 28 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  labelRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  label: { color: COLORS.text, fontSize: 14, fontWeight: '600' },
  val: { color: COLORS.accent, fontSize: 14, fontWeight: '700' },
  desc: { color: COLORS.textDim, fontSize: 12, lineHeight: 17, marginBottom: 10 },
  rangeRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  rangeText: { color: COLORS.textMuted, fontSize: 10 },
  dbRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10 },
  checkbox: {
    width: 22, height: 22, borderRadius: 6,
    borderWidth: 2, borderColor: COLORS.textMuted,
    alignItems: 'center', justifyContent: 'center',
  },
  checkboxOn: { backgroundColor: COLORS.red, borderColor: COLORS.red },
  dbText: { color: COLORS.textDim, fontSize: 13, fontWeight: '500' },
});
