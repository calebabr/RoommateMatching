import React, { useRef } from 'react';
import { View, PanResponder } from 'react-native';
import { COLORS } from '../constants/theme';

const TRACK_H = 6;
const THUMB = 22;

export default function Slider({ value, min = 0, max = 10, onValueChange }) {
  const trackRef = useRef(null);
  const pct = ((value - min) / (max - min)) * 100;

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) => touch(e),
      onPanResponderMove: (e) => touch(e),
    })
  ).current;

  function touch(e) {
    if (!trackRef.current) return;
    trackRef.current.measure((_x, _y, width) => {
      if (!width) return;
      const ratio = Math.max(0, Math.min(1, e.nativeEvent.locationX / width));
      const v = Math.round(min + ratio * (max - min));
      if (v !== value) onValueChange(v);
    });
  }

  return (
    <View ref={trackRef} style={{ height: 30, justifyContent: 'center' }} {...pan.panHandlers}>
      <View style={{ position: 'absolute', left: 0, right: 0, height: TRACK_H, borderRadius: 3, backgroundColor: COLORS.surfaceAlt }} />
      <View style={{ position: 'absolute', left: 0, height: TRACK_H, borderRadius: 3, backgroundColor: COLORS.accent, width: `${pct}%` }} />
      <View
        style={{
          position: 'absolute',
          width: THUMB,
          height: THUMB,
          borderRadius: THUMB / 2,
          backgroundColor: COLORS.accent,
          borderWidth: 3,
          borderColor: COLORS.bg,
          left: `${pct}%`,
          marginLeft: -THUMB / 2,
          elevation: 4,
          shadowColor: COLORS.accent,
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.4,
          shadowRadius: 6,
        }}
      />
    </View>
  );
}
