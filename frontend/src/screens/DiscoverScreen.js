import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Alert,
  ActivityIndicator, Animated,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import Avatar from '../components/Avatar';
import CompatBadge from '../components/CompatBadge';
import PrefTag from '../components/PrefTag';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, RADIUS } from '../constants/theme';

export default function DiscoverScreen() {
  const { user } = useAuth();
  const [recs, setRecs] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [slideAnim] = useState(new Animated.Value(0));
  const [fadeAnim] = useState(new Animated.Value(1));

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const [r, u] = await Promise.all([
        api.getTopMatches(user.id).catch(() => ({ matches: [] })),
        api.getAllUsers().catch(() => []),
      ]);
      setRecs(r.matches || []);
      setAllUsers(u);
      setIdx(0);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const getUser = (id) => allUsers.find((u) => u.id === id);
  const cur = recs[idx];
  const recUser = cur ? getUser(cur.user_id) : null;

  const swipe = (dir, cb) => {
    Animated.parallel([
      Animated.timing(slideAnim, { toValue: dir === 'right' ? 400 : -400, duration: 300, useNativeDriver: true }),
      Animated.timing(fadeAnim, { toValue: 0, duration: 250, useNativeDriver: true }),
    ]).start(() => { cb(); slideAnim.setValue(0); fadeAnim.setValue(1); });
  };

  const handleLike = async () => {
    if (!cur || busy) return;
    setBusy(true);
    swipe('right', async () => {
      try {
        const res = await api.likeUser(user.id, cur.user_id);
        if (res.status === 'matched') {
          Alert.alert('It\'s a Match!', `You matched with ${recUser?.username || 'someone'}!`);
        }
        setIdx((i) => i + 1);
      } catch (e) { Alert.alert('Error', e.message); }
      finally { setBusy(false); }
    });
  };

  const handlePass = () => {
    swipe('left', () => setIdx((i) => Math.min(i + 1, recs.length)));
  };

  if (loading) {
    return <View style={st.center}><ActivityIndicator size="large" color={COLORS.accent} /></View>;
  }

  if (!cur || idx >= recs.length) {
    return (
      <View style={st.center}>
        <Feather name="zap" size={48} color={COLORS.textMuted} />
        <Text style={st.emptyTitle}>All caught up!</Text>
        <Text style={st.emptyText}>Check back later for new recommendations</Text>
        <TouchableOpacity style={st.refreshBtn} onPress={load}>
          <Text style={{ color: COLORS.accent, fontWeight: '600' }}>Refresh</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const display = recUser || { username: `User #${cur.user_id}`, id: cur.user_id };

  return (
    <View style={st.container}>
      <Animated.View style={[st.card, { transform: [{ translateX: slideAnim }], opacity: fadeAnim }]}>
        <View style={st.cardTop}>
          <View style={st.topDecor} />
          <Avatar uri={display.profilePic} name={display.username} size={120} />
          <View style={st.badgePos}>
            <CompatBadge score={cur.compatibilityScore} />
          </View>
        </View>
        <View style={st.cardBody}>
          <Text style={st.cardName}>{display.username}</Text>
          <Text style={st.cardBio}>{display.bio || 'No bio yet'}</Text>
          <View style={st.tags}>
            {display.sleepScoreWD && <>
              <PrefTag icon="moon" label={`Sleep ${display.sleepScoreWD.value}:00`} isDealBreaker={display.sleepScoreWD.isDealBreaker} />
              <PrefTag icon="star" label={`Clean ${display.cleanlinessScore?.value}/10`} isDealBreaker={display.cleanlinessScore?.isDealBreaker} />
              <PrefTag icon="volume-2" label={`Noise ${display.noiseToleranceScore?.value}/10`} isDealBreaker={display.noiseToleranceScore?.isDealBreaker} />
              <PrefTag icon="users" label={`Guests ${display.guestsScore?.value}/10`} isDealBreaker={display.guestsScore?.isDealBreaker} />
            </>}
          </View>
        </View>
      </Animated.View>

      <View style={st.actions}>
        <TouchableOpacity style={st.passBtn} onPress={handlePass}>
          <Feather name="x" size={28} color={COLORS.red} />
        </TouchableOpacity>
        <TouchableOpacity style={st.likeBtn} onPress={handleLike}>
          <Feather name="heart" size={30} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const st = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg, padding: 20, paddingTop: 8 },
  center: { flex: 1, backgroundColor: COLORS.bg, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: COLORS.textDim, marginTop: 16 },
  emptyText: { color: COLORS.textMuted, fontSize: 14, marginTop: 8 },
  refreshBtn: { marginTop: 20, borderWidth: 1.5, borderColor: COLORS.accent, borderRadius: RADIUS.md, paddingVertical: 12, paddingHorizontal: 28 },
  card: { flex: 1, backgroundColor: COLORS.card, borderRadius: 24, overflow: 'hidden' },
  cardTop: { height: 220, backgroundColor: COLORS.surfaceAlt, alignItems: 'center', justifyContent: 'center', position: 'relative' },
  topDecor: { position: 'absolute', top: 0, right: 0, width: 200, height: 200, borderRadius: 100, backgroundColor: COLORS.accentGlow, opacity: 0.3 },
  badgePos: { position: 'absolute', top: 16, right: 16 },
  cardBody: { padding: 20 },
  cardName: { fontSize: 24, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  cardBio: { color: COLORS.textDim, fontSize: 13, marginBottom: 20 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  actions: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 24, marginTop: 20, paddingBottom: 8 },
  passBtn: { width: 64, height: 64, borderRadius: 32, backgroundColor: COLORS.surfaceAlt, borderWidth: 2, borderColor: COLORS.border, alignItems: 'center', justifyContent: 'center' },
  likeBtn: {
    width: 72, height: 72, borderRadius: 36, backgroundColor: COLORS.accent,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: COLORS.accent, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 12, elevation: 8,
  },
});
