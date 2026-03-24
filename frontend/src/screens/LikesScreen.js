import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Image,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getLikesReceived, sendLike, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';

export default function LikesScreen() {
  const navigation = useNavigation();
  const { user, refreshUser } = useAuth();
  const insets = useSafeAreaInsets();
  const [likes, setLikes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionId, setActionId] = useState(null);

  const loadLikes = async () => {
    if (!user?.id) return;
    try {
      const raw = await getLikesReceived(user.id);
      const enriched = await Promise.all(
        raw.map(async (like) => {
          try {
            const profile = await getUser(like.fromUser);
            return { ...like, profile };
          } catch {
            return { ...like, profile: { id: like.fromUser, username: `User #${like.fromUser}` } };
          }
        })
      );
      setLikes(enriched);
    } catch {
      setLikes([]);
    }
  };

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        setLoading(true);
        await loadLikes();
        if (active) setLoading(false);
      })();
      return () => { active = false; };
    }, [user?.id])
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadLikes();
    setRefreshing(false);
  };

  const handleLikeBack = async (fromUserId) => {
    setActionId(fromUserId);
    try {
      const result = await sendLike(user.id, fromUserId);
      if (result.status === 'matched') {
        Alert.alert('🎉 Match!', `You and User #${fromUserId} are now roommate matches!`);
        await refreshUser();
      } else {
        Alert.alert('Liked!', 'Your like has been sent.');
      }
      await loadLikes();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send like.';
      Alert.alert('Error', msg);
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  const renderLike = ({ item }) => {
    const p = item.profile;
    const photoSrc = getPhotoUrl(p?.photoUrl);
    return (
      <View style={styles.card}>
        <TouchableOpacity
          style={styles.cardBody}
          onPress={() => navigation.navigate('UserDetail', { userId: p.id })}
          activeOpacity={0.8}
        >
          {photoSrc ? (
            <Image source={{ uri: photoSrc }} style={styles.avatarImage} />
          ) : (
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(p.username || '?')[0].toUpperCase()}
            </Text>
          </View>
          )}
          <View style={styles.cardInfo}>
            <Text style={styles.cardName}>{p.username || `User #${p.id}`}</Text>
            <Text style={styles.cardSub}>Wants to be your roommate!</Text>
          </View>
        </TouchableOpacity>

        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.likeBackBtn}
            onPress={() => handleLikeBack(p.id)}
            disabled={actionId === p.id}
            activeOpacity={0.7}
          >
            {actionId === p.id ? (
              <ActivityIndicator size="small" color={Colors.black} />
            ) : (
              <Text style={styles.likeBackText}>♥ Like Back</Text>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.viewBtn}
            onPress={() => navigation.navigate('UserDetail', { userId: p.id })}
            activeOpacity={0.7}
          >
            <Text style={styles.viewBtnText}>View Profile</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
        <View>
          <Text style={styles.headerTitle}>Likes</Text>
          <Text style={styles.headerSub}>
            {likes.length} {likes.length === 1 ? 'person likes' : 'people like'} you
          </Text>
        </View>
        <NotificationBell onPress={() => navigation.navigate('Notifications')} />
      </View>

      {likes.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emoji}>💌</Text>
          <Text style={styles.emptyTitle}>No Likes Yet</Text>
          <Text style={styles.emptySubtitle}>
            When someone likes you, they'll appear here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={likes}
          keyExtractor={(item, i) => `${item.fromUser}-${i}`}
          renderItem={renderLike}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.accent} />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary },
  headerSub: { fontSize: 13, color: Colors.textSecondary, marginTop: 2 },
  list: { paddingHorizontal: 20, paddingBottom: 30 },
  card: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: 20,
    marginTop: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardBody: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.dangerDim,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.danger,
  },
  avatarImage: {
    width: 52,
    height: 52,
    borderRadius: 26,
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.danger,
    backgroundColor: Colors.bgCard,
  },
  avatarText: { fontSize: 22, fontWeight: '800', color: Colors.danger },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary },
  cardSub: { fontSize: 13, color: Colors.textSecondary, marginTop: 2 },
  actions: { flexDirection: 'row', gap: 10 },
  likeBackBtn: {
    flex: 1,
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 12,
    alignItems: 'center',
  },
  likeBackText: { fontSize: 14, fontWeight: '700', color: Colors.black },
  viewBtn: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingVertical: 12,
    alignItems: 'center',
  },
  viewBtnText: { fontSize: 14, fontWeight: '600', color: Colors.textSecondary },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emoji: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
});