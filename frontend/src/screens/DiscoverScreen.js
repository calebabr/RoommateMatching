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
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getTopMatches, sendLike, getLikesSent, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';

export default function DiscoverScreen() {
  const navigation = useNavigation();
  const { user, refreshUser } = useAuth();
  const insets = useSafeAreaInsets();
  const [matches, setMatches] = useState([]);
  const [matchProfiles, setMatchProfiles] = useState([]);
  const [likedIds, setLikedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [likingId, setLikingId] = useState(null);

  const loadMatches = async () => {
    if (!user?.id) return;
    try {
      const [data, sentIds] = await Promise.all([
        getTopMatches(user.id),
        getLikesSent(user.id),
      ]);
      const topList = data.matches || [];
      setMatches(topList);
      setLikedIds(new Set(sentIds));

      const profiles = await Promise.all(
        topList.map(async (m) => {
          try {
            const profile = await getUser(m.user_id);
            return { ...profile, compatibilityScore: m.compatibilityScore };
          } catch {
            return { id: m.user_id, username: `User #${m.user_id}`, compatibilityScore: m.compatibilityScore };
          }
        })
      );
      setMatchProfiles(profiles);
    } catch {
      setMatchProfiles([]);
    }
  };

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        setLoading(true);
        await refreshUser();
        await loadMatches();
        if (active) setLoading(false);
      })();
      return () => { active = false; };
    }, [user?.id])
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadMatches();
    setRefreshing(false);
  };

  const handleLike = async (targetId) => {
    setLikingId(targetId);
    try {
      const result = await sendLike(user.id, targetId);
      if (result.status === 'matched') {
        Alert.alert('🎉 It\'s a Match!', `You and User #${targetId} are now roommate matches!`);
        await refreshUser();
        await loadMatches();
      } else {
        // Mark as pending locally — keep card visible but show Pending state
        setLikedIds((prev) => new Set([...prev, targetId]));
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send like.';
      Alert.alert('Error', msg);
    } finally {
      setLikingId(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
        <Text style={styles.loadingText}>Finding compatible roommates...</Text>
      </View>
    );
  }

  if (matchProfiles.length === 0) {
    return (
      <View style={styles.container}>
        <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
          <View>
            <Text style={styles.headerTitle}>Discover</Text>
            <Text style={styles.headerSub}>Find your roommate</Text>
          </View>
          <NotificationBell onPress={() => navigation.navigate('Notifications')} />
        </View>
        <View style={styles.centered}>
          <Text style={styles.emoji}>🔍</Text>
          <Text style={styles.emptyTitle}>No Matches Yet</Text>
          <Text style={styles.emptySubtitle}>
            New users are being added all the time. Pull down to refresh!
          </Text>
          <TouchableOpacity style={styles.refreshBtn} onPress={handleRefresh}>
            <Text style={styles.refreshBtnText}>Refresh</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const renderMatch = ({ item }) => {
    const score = item.compatibilityScore;
    const color = getCompatibilityColor(score);
    const label = getCompatibilityLabel(score);
    const myTags = user?.lifestyleTags || [];
    const theirTags = item.lifestyleTags || [];
    const sharedTags = myTags.filter((t) => theirTags.includes(t));
    const photoSrc = getPhotoUrl(item.photoUrl);

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('UserDetail', { userId: item.id, score })}
        activeOpacity={0.85}
      >
        <View style={[styles.scoreBadge, { backgroundColor: color + '20', borderColor: color }]}>
          <Text style={[styles.scorePercent, { color }]}>{Math.round(score * 100)}%</Text>
          <Text style={[styles.scoreLabel, { color }]}>{label}</Text>
        </View>

        <View style={styles.cardBody}>
          {photoSrc ? (
            <Image source={{ uri: photoSrc }} style={styles.avatarImage} />
          ) : (
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(item.username || '?')[0].toUpperCase()}
              </Text>
            </View>
          )}
          <View style={styles.cardInfo}>
            <Text style={styles.cardName}>{item.username || `User #${item.id}`}</Text>
            {item.gender && (
              <Text style={styles.genderTag}>
                {item.gender === 'male' ? '♂ Male' : '♀ Female'}
              </Text>
            )}
            {item.bio ? (
              <Text style={styles.cardBio} numberOfLines={2}>{item.bio}</Text>
            ) : (
              <Text style={styles.cardId}>ID: {item.id}</Text>
            )}
          </View>
        </View>

        {theirTags.length > 0 && (
          <View style={styles.tagRow}>
            {theirTags.slice(0, 6).map((tag) => {
              const isShared = sharedTags.includes(tag);
              return (
                <View key={tag} style={[styles.tagPill, isShared && styles.tagPillShared]}>
                  <Text style={[styles.tagPillText, isShared && styles.tagPillTextShared]}>{tag}</Text>
                </View>
              );
            })}
            {theirTags.length > 6 && (
              <Text style={styles.tagMore}>+{theirTags.length - 6}</Text>
            )}
          </View>
        )}

        {sharedTags.length > 0 && (
          <Text style={styles.sharedNote}>
            {sharedTags.length} shared {sharedTags.length === 1 ? 'interest' : 'interests'}
          </Text>
        )}

        <View style={styles.prefBars}>
          {CATEGORIES.map((cat) => {
            const pref = item[cat.key];
            if (!pref) return null;
            const pct = (pref.value / cat.max) * 100;
            return (
              <View key={cat.key} style={styles.miniBar}>
                <Text style={styles.miniBarLabel} numberOfLines={1}>
                  {cat.label.replace(' (Weekdays)', ' WD').replace(' (Weekends)', ' WE').replace('Smoking / Substances', 'Smoking')}
                </Text>
                <View style={styles.miniBarTrack}>
                  <View style={[styles.miniBarFill, { width: `${pct}%` }]} />
                </View>
                <Text style={styles.miniBarVal}>{Math.round(pref.value)}</Text>
              </View>
            );
          })}
        </View>

        {likedIds.has(item.id) ? (
          <View style={styles.pendingBtn}>
            <Text style={styles.pendingBtnText}>✓ Pending</Text>
          </View>
        ) : (
          <TouchableOpacity
            style={styles.likeBtn}
            onPress={() => handleLike(item.id)}
            disabled={likingId === item.id}
            activeOpacity={0.7}
          >
            {likingId === item.id ? (
              <ActivityIndicator size="small" color={Colors.black} />
            ) : (
              <Text style={styles.likeBtnText}>♥ Like</Text>
            )}
          </TouchableOpacity>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
        <View>
          <Text style={styles.headerTitle}>Discover</Text>
          <Text style={styles.headerSub}>{matchProfiles.length} compatible roommates</Text>
        </View>
        <NotificationBell onPress={() => navigation.navigate('Notifications')} />
      </View>
      <FlatList
        data={matchProfiles}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderMatch}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.accent} />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary },
  headerSub: { fontSize: 13, color: Colors.textSecondary, marginTop: 2 },
  list: { paddingHorizontal: 20, paddingBottom: 30 },
  card: { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 20, marginTop: 16, borderWidth: 1, borderColor: Colors.border },
  scoreBadge: { alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 5, borderRadius: Radius.full, borderWidth: 1, marginBottom: 14, gap: 6 },
  scorePercent: { fontSize: 16, fontWeight: '800' },
  scoreLabel: { fontSize: 12, fontWeight: '600' },
  cardBody: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  avatar: { width: 48, height: 48, borderRadius: 24, backgroundColor: Colors.accentGlow, alignItems: 'center', justifyContent: 'center', marginRight: 14, borderWidth: 2, borderColor: Colors.accent },
  avatarImage: { width: 48, height: 48, borderRadius: 24, marginRight: 14, borderWidth: 2, borderColor: Colors.accent, backgroundColor: Colors.bgCard },
  avatarText: { fontSize: 20, fontWeight: '800', color: Colors.accent },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary },
  genderTag: { fontSize: 12, color: Colors.info, fontWeight: '600', marginTop: 2 },
  cardBio: { fontSize: 13, color: Colors.textSecondary, marginTop: 2, lineHeight: 18 },
  cardId: { fontSize: 12, color: Colors.textMuted, marginTop: 2 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  tagPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: Radius.full, borderWidth: 1, borderColor: Colors.border, backgroundColor: Colors.bgCardLight },
  tagPillShared: { borderColor: Colors.success, backgroundColor: Colors.successDim },
  tagPillText: { fontSize: 11, fontWeight: '600', color: Colors.textMuted },
  tagPillTextShared: { color: Colors.success },
  tagMore: { fontSize: 11, color: Colors.textMuted, alignSelf: 'center' },
  sharedNote: { fontSize: 12, fontWeight: '600', color: Colors.success, marginBottom: 10 },
  prefBars: { marginBottom: 16 },
  miniBar: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  miniBarLabel: { fontSize: 11, color: Colors.textMuted, width: 80 },
  miniBarTrack: { flex: 1, height: 4, backgroundColor: Colors.border, borderRadius: 2, marginHorizontal: 8, overflow: 'hidden' },
  miniBarFill: { height: '100%', backgroundColor: Colors.accent, borderRadius: 2 },
  miniBarVal: { fontSize: 11, color: Colors.textSecondary, width: 20, textAlign: 'right' },
  likeBtn: { backgroundColor: Colors.accent, borderRadius: Radius.md, paddingVertical: 12, alignItems: 'center' },
  likeBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
  pendingBtn: { borderWidth: 1.5, borderColor: Colors.border, borderRadius: Radius.md, paddingVertical: 12, alignItems: 'center' },
  pendingBtnText: { fontSize: 15, fontWeight: '600', color: Colors.textMuted },
  centered: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emoji: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
  refreshBtn: { marginTop: 24, backgroundColor: Colors.accent, borderRadius: Radius.md, paddingVertical: 12, paddingHorizontal: 32 },
  refreshBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
  loadingText: { fontSize: 14, color: Colors.textSecondary, marginTop: 16 },
});