import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Alert, ActivityIndicator,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import Avatar from '../components/Avatar';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, RADIUS } from '../constants/theme';

export default function LikesScreen() {
  const { user } = useAuth();
  const [likes, setLikes] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const [l, u] = await Promise.all([
        api.getLikesReceived(user.id).catch(() => []),
        api.getAllUsers().catch(() => []),
      ]);
      setLikes(l);
      setAllUsers(u);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const getUser = (id) => allUsers.find((u) => u.id === id);

  const handleLikeBack = async (fromId) => {
    try {
      const res = await api.likeUser(user.id, fromId);
      if (res.status === 'matched') {
        Alert.alert('It\'s a Match!', 'Check your Matches tab!');
      }
      setLikes((p) => p.filter((l) => l.fromUser !== fromId));
    } catch (e) { Alert.alert('Error', e.message); }
  };

  const renderItem = ({ item }) => {
    const lu = getUser(item.fromUser) || { username: `User #${item.fromUser}` };
    return (
      <View style={st.card}>
        <Avatar uri={lu.profilePic} name={lu.username} size={50} />
        <View style={st.info}>
          <Text style={st.name}>{lu.username}</Text>
          <Text style={st.bio}>{lu.bio || 'Wants to connect'}</Text>
        </View>
        <View style={st.actions}>
          <TouchableOpacity style={st.acceptBtn} onPress={() => handleLikeBack(item.fromUser)}>
            <Feather name="heart" size={18} color="#fff" />
          </TouchableOpacity>
          <TouchableOpacity style={st.declineBtn}>
            <Feather name="x" size={18} color={COLORS.textDim} />
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  if (loading) return <View style={st.center}><ActivityIndicator size="large" color={COLORS.accent} /></View>;

  return (
    <View style={st.container}>
      <Text style={st.heading}>Who likes you</Text>
      <Text style={st.sub}>{likes.length} pending {likes.length === 1 ? 'like' : 'likes'}</Text>
      {likes.length === 0 ? (
        <View style={st.empty}>
          <Feather name="heart" size={40} color={COLORS.textMuted} />
          <Text style={st.emptyText}>No likes yet — keep discovering!</Text>
        </View>
      ) : (
        <FlatList data={likes} keyExtractor={(i) => String(i.fromUser)} renderItem={renderItem}
          contentContainerStyle={{ paddingBottom: 20 }} />
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
  card: { backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center', gap: 14 },
  info: { flex: 1 },
  name: { color: COLORS.text, fontWeight: '700', fontSize: 15 },
  bio: { color: COLORS.textDim, fontSize: 12, marginTop: 2 },
  actions: { flexDirection: 'row', gap: 8 },
  acceptBtn: { width: 42, height: 42, borderRadius: 21, backgroundColor: COLORS.green, alignItems: 'center', justifyContent: 'center' },
  declineBtn: { width: 42, height: 42, borderRadius: 21, backgroundColor: COLORS.surfaceAlt, borderWidth: 1, borderColor: COLORS.border, alignItems: 'center', justifyContent: 'center' },
});
