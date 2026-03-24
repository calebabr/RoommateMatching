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
import { useFocusEffect } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getTopMatches, sendLike, getUser, getPhotoUrl } from '../services/api';

export default function DiscoverScreen({ navigation }) {
  const insets = useSafeAreaInsets();
  const { user, refreshUser } = useAuth();
  const [matches, setMatches] = useState([]);
  const [matchProfiles, setMatchProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [likingId, setLikingId] = useState(null);

  const loadMatches = async () => {
    if (!user?.id) return;
    try {
      const data = await getTopMatches(user.id);
      const topList = data.matches || [];
      setMatches(topList);

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
        Alert.alert('Like Sent!', 'They\'ll see your interest. Fingers crossed!');
        setMatchProfiles((prev) => prev.filter((p) => p.id !== targetId));
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send like.';
      Alert.alert('Error', msg);
    } finally {
      setLikingId(null);
    }
  };

  if (user?.matched) {
    return (
      <View style={[styles.centered, { paddingTop: insets.top }]}>
        <Text style={styles.emoji}>🎉</Text>
        <Text style={styles.matchedTitle}>You're Matched!</Text>
        <Text style={styles.matchedSubtitle}>
          Head to the Matches tab to see your roommate.
        </Text>
      </View>
    );
  }

  if (loading) {
    return (
      <View style={[styles.centered, { paddingTop: insets.top }]}>
        <ActivityIndicator size="large" color={Colors.accent} />
        <Text style={styles.loadingText}>Finding compatible roommates...</Text>
      </View>
    );
  }

  if (matchProfiles.length === 0) {
    return (
      <View style={[styles.centered, { paddingTop: insets.top }]}>
        <Text style={styles.emoji}>🔍</Text>
        <Text style={styles.emptyTitle}>No Matches Yet</Text>
        <Text style={styles.emptySubtitle}>
          New users are being added all the time. Pull down to refresh!
        </Text>
        <TouchableOpacity style={styles.refreshBtn} onPress={handleRefresh}>
          <Text style={styles.refreshBtnText}>Refresh</Text>
        </TouchableOpacity>
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

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('UserDetail', { userId: item.id, score })}
        activeOpacity={0.85}
      >
        {/* Score badge */}
        <View style={[styles.scoreBadge, { backgroundColor: color + '20', borderColor: color }]}>
          <Text style={[styles.scorePercent, { color }]}>{Math.round(score * 100)}%</Text>
          <Text style={[styles.scoreLabel, { color }]}>{label}</Text>
        </View>

        {/* User info */}
        <View style={styles.cardBody}>
          {getPhotoUrl(item.photoUrl) ? (
            <Image source={{ uri: getPhotoUrl(item.photoUrl) }} style={styles.avatarImage} />
          ) : (
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(item.username || '?')[0].toUpperCase()}
              </Text>
            </View>
          )}
          <View style={styles.cardInfo}>
            <Text style={styles.cardName}>{item.username || `User #${item.id}`}</Text>
            {item.bio ? (
              <Text style={styles.cardBio} numberOfLines={2}>{item.bio}</Text>
            ) : (
              <Text style={styles.cardId}>ID: {item.id}</Text>
            )}
          </View>
        </View>

        {/* Lifestyle Tags */}
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

        {/* Mini preference bars */}
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

        {/* Like button */}
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
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <Text style={styles.headerTitle}>Discover</Text>
        <Text style={styles.headerSub}>{matchProfiles.length} compatible roommates</Text>
      </View>
      <FlatList
        data={matchProfiles}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderMatch}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={Colors.accent}
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
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
  scoreBadge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: Radius.full,
    borderWidth: 1,
    marginBottom: 14,
    gap: 6,
  },
  scorePercent: { fontSize: 16, fontWeight: '800' },
  scoreLabel: { fontSize: 12, fontWeight: '600' },
  cardBody: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Colors.accentGlow,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.accent,
  },
  avatarImage: {
    width: 48,
    height: 48,
    borderRadius: 24,
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.accent,
    backgroundColor: Colors.bgCard,
  },
  avatarText: { fontSize: 20, fontWeight: '800', color: Colors.accent },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary },
  cardBio: { fontSize: 13, color: Colors.textSecondary, marginTop: 2, lineHeight: 18 },
  cardId: { fontSize: 12, color: Colors.textMuted, marginTop: 2 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  tagPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.bgCardLight,
  },
  tagPillShared: { borderColor: Colors.success, backgroundColor: Colors.successDim },
  tagPillText: { fontSize: 11, fontWeight: '600', color: Colors.textMuted },
  tagPillTextShared: { color: Colors.success },
  tagMore: { fontSize: 11, color: Colors.textMuted, alignSelf: 'center' },
  sharedNote: { fontSize: 12, fontWeight: '600', color: Colors.success, marginBottom: 10 },
  prefBars: { marginBottom: 16 },
  miniBar: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  miniBarLabel: { fontSize: 11, color: Colors.textMuted, width: 80 },
  miniBarTrack: {
    flex: 1,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: 2,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  miniBarFill: { height: '100%', backgroundColor: Colors.accent, borderRadius: 2 },
  miniBarVal: { fontSize: 11, color: Colors.textSecondary, width: 20, textAlign: 'right' },
  likeBtn: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 12,
    alignItems: 'center',
  },
  likeBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
  centered: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emoji: { fontSize: 56, marginBottom: 16 },
  matchedTitle: { fontSize: 24, fontWeight: '800', color: Colors.success, marginBottom: 8 },
  matchedSubtitle: { fontSize: 15, color: Colors.textSecondary, textAlign: 'center' },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
  refreshBtn: {
    marginTop: 24,
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 12,
    paddingHorizontal: 32,
  },
  refreshBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
  loadingText: { fontSize: 14, color: Colors.textSecondary, marginTop: 16 },
});