import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Alert, ActivityIndicator,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import Avatar from '../components/Avatar';
import CompatBadge from '../components/CompatBadge';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, RADIUS } from '../constants/theme';

export default function MatchesScreen() {
  const { user } = useAuth();
  const [matches, setMatches] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const [m, u] = await Promise.all([
        api.getMatches(user.id).catch(() => []),
        api.getAllUsers().catch(() => []),
      ]);
      setMatches(m);
      setAllUsers(u);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const getUser = (id) => allUsers.find((u) => u.id === id);

  const handleUnmatch = (partnerId, name) => {
    Alert.alert('Unmatch', `Are you sure you want to unmatch with ${name}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Unmatch', style: 'destructive',
        onPress: async () => {
          try {
            await api.unmatchUser(user.id);
            setMatches((p) => p.filter((m) => m.user1_id !== partnerId && m.user2_id !== partnerId));
          } catch (e) { Alert.alert('Error', e.message); }
        },
      },
    ]);
  };

  const renderItem = ({ item }) => {
    const pid = item.user1_id === user.id ? item.user2_id : item.user1_id;
    const partner = getUser(pid) || { username: `User #${pid}` };
    return (
      <View style={st.card}>
        <View style={st.row}>
          <View>
            <Avatar uri={partner.profilePic} name={partner.username} size={56} />
            <View style={st.checkBadge}><Feather name="check" size={10} color="#fff" /></View>
          </View>
          <View style={st.info}>
            <Text style={st.name}>{partner.username}</Text>
            <Text style={st.matchLabel}>Matched!</Text>
          </View>
          {item.compatibilityScore != null && <CompatBadge score={item.compatibilityScore} size={44} />}
        </View>
        <TouchableOpacity style={st.unmatchBtn} onPress={() => handleUnmatch(pid, partner.username)}>
          <Text style={st.unmatchText}>Unmatch</Text>
        </TouchableOpacity>
      </View>
    );
  };

  if (loading) return <View style={st.center}><ActivityIndicator size="large" color={COLORS.accent} /></View>;

  return (
    <View style={st.container}>
      <Text style={st.heading}>Your matches</Text>
      <Text style={st.sub}>{matches.length} confirmed {matches.length === 1 ? 'match' : 'matches'}</Text>
      {matches.length === 0 ? (
        <View style={st.empty}>
          <Feather name="link" size={40} color={COLORS.textMuted} />
          <Text style={st.emptyText}>No matches yet — like people to connect!</Text>
        </View>
      ) : (
        <FlatList data={matches} keyExtractor={(i) => i._id || `${i.user1_id}-${i.user2_id}`}
          renderItem={renderItem} contentContainerStyle={{ paddingBottom: 20 }} />
      )}
    </View>
  );
}

const st = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg, paddingHorizontal: 20, paddingTop: 8 },
  center: { flex: 1, backgroundColor: COLORS.bg, justifyContent: 'center', alignItems: 'center' },
  heading: { fontSize: 22, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  sub: { color: COLORS.textDim, fontSize: 13, marginBottom: 20 },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: COLORS.textMuted, marginTop: 12, fontSize: 14 },
  card: { backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: 20, marginBottom: 12, borderWidth: 1, borderColor: 'rgba(232,168,56,0.15)' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  checkBadge: {
    position: 'absolute', bottom: -2, right: -2, width: 18, height: 18, borderRadius: 9,
    backgroundColor: COLORS.green, borderWidth: 2, borderColor: COLORS.card,
    alignItems: 'center', justifyContent: 'center',
  },
  info: { flex: 1 },
  name: { color: COLORS.text, fontWeight: '700', fontSize: 16 },
  matchLabel: { color: COLORS.green, fontSize: 12, fontWeight: '600', marginTop: 2 },
  unmatchBtn: { marginTop: 14, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.sm, padding: 12, alignItems: 'center' },
  unmatchText: { color: COLORS.textDim, fontSize: 13, fontWeight: '500' },
});
