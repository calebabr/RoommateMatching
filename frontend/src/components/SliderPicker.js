import React, { useRef } from 'react';
import { View, Text, PanResponder, StyleSheet } from 'react-native';
import { Colors, Radius } from '../utils/theme';

export default function SliderPicker({ min, max, value, onChange, formatLabel }) {
  const trackRef = useRef(null);
  const range = max - min;
  const pct = ((value - min) / range) * 100;

  const handleTouch = (evt) => {
    trackRef.current?.measure((_x, _y, width, _h, pageX) => {
      const touch = evt.nativeEvent.pageX - pageX;
      const clamped = Math.min(Math.max(touch / width, 0), 1);
      const stepped = Math.round(clamped * range + min);
      onChange(stepped);
    });
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: handleTouch,
      onPanResponderMove: handleTouch,
    })
  ).current;

  return (
    <View style={styles.wrapper}>
      <View style={styles.labelRow}>
        <Text style={styles.value}>{formatLabel ? formatLabel(value) : value}</Text>
      </View>
      <View
        ref={trackRef}
        style={styles.track}
        {...panResponder.panHandlers}
      >
        <View style={[styles.fill, { width: `${pct}%` }]} />
        <View style={[styles.thumb, { left: `${pct}%` }]} />
      </View>
      <View style={styles.rangeRow}>
        <Text style={styles.rangeText}>{min}</Text>
        <Text style={styles.rangeText}>{max}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { marginTop: 4 },
  labelRow: { alignItems: 'center', marginBottom: 10 },
  value: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.accent,
  },
  track: {
    height: 6,
    backgroundColor: Colors.border,
    borderRadius: 3,
    justifyContent: 'center',
    position: 'relative',
  },
  fill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: Colors.accent,
    borderRadius: 3,
  },
  thumb: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colors.accent,
    borderWidth: 3,
    borderColor: Colors.bg,
    marginLeft: -12,
    top: -9,
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 4,
  },
  rangeRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 },
  rangeText: { fontSize: 11, color: Colors.textMuted },
});
