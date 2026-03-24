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
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getMatches, getUser, unmatchUser, getMatchScore } from '../services/api';
import NotificationBell from '../components/NotificationBell';

export default function MatchesScreen() {
  const navigation = useNavigation();
  const { user, refreshUser } = useAuth();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadMatches = async () => {
    if (!user?.id) return;
    try {
      const raw = await getMatches(user.id);
      const enriched = await Promise.all(
        raw.map(async (match) => {
          const partnerId = match.user1_id === user.id ? match.user2_id : match.user1_id;
          try {
            const profile = await getUser(partnerId);
            let score = null;
            try {
              const scoreData = await getMatchScore(user.id, partnerId);
              score = scoreData.compatibilityScore;
            } catch {}
            return { ...match, profile, compatibilityScore: score };
          } catch {
            return { ...match, profile: { id: partnerId, username: `User #${partnerId}` }, compatibilityScore: null };
          }
        })
      );
      setMatches(enriched);
    } catch {
      setMatches([]);
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
    await refreshUser();
    await loadMatches();
    setRefreshing(false);
  };

  const handleUnmatch = async (matchedUserId) => {
    Alert.alert(
      'Unmatch',
      'Are you sure you want to unmatch? You\'ll both return to the matching pool.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unmatch',
          style: 'destructive',
          onPress: async () => {
            try {
              await unmatchUser(user.id);
              await refreshUser();
              await loadMatches();
              Alert.alert('Unmatched', 'You are back in the matching pool.');
            } catch (err) {
              const msg = err?.response?.data?.detail || 'Could not unmatch.';
              Alert.alert('Error', msg);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  const renderMatch = ({ item }) => {
    const p = item.profile;
    const score = item.compatibilityScore;

    return (
      <View style={styles.card}>
        <View style={styles.matchBanner}>
          <Text style={styles.matchEmoji}>🤝</Text>
          <Text style={styles.matchLabel}>Roommate Match</Text>
          {score !== null && (
            <View style={styles.scorePill}>
              <Text style={styles.scorePillText}>{Math.round(score * 100)}% compatible</Text>
            </View>
          )}
        </View>

        <TouchableOpacity
          style={styles.cardBody}
          onPress={() => navigation.navigate('UserDetail', { userId: p.id, score })}
          activeOpacity={0.8}
        >
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {(p.username || '?')[0].toUpperCase()}
            </Text>
          </View>
          <View style={styles.cardInfo}>
            <Text style={styles.cardName}>{p.username || `User #${p.id}`}</Text>
            <Text style={styles.cardId}>ID: {p.id}</Text>
          </View>
        </TouchableOpacity>

        {/* Preference comparison */}
        {p.sleepScoreWD && (
          <View style={styles.comparison}>
            <Text style={styles.compTitle}>Preference Comparison</Text>
            {CATEGORIES.map((cat) => {
              const mine = user[cat.key]?.value;
              const theirs = p[cat.key]?.value;
              if (mine == null || theirs == null) return null;
              const diff = Math.abs(mine - theirs);
              const maxDiff = cat.max - cat.min;
              const similarity = Math.round(((maxDiff - diff) / maxDiff) * 100);
              return (
                <View key={cat.key} style={styles.compRow}>
                  <Text style={styles.compLabel}>
                    {cat.label.replace(' (Weekdays)', ' WD').replace(' (Weekends)', ' WE')}
                  </Text>
                  <View style={styles.compValues}>
                    <Text style={styles.compYou}>{Math.round(mine)}</Text>
                    <Text style={styles.compVs}>vs</Text>
                    <Text style={styles.compThem}>{Math.round(theirs)}</Text>
                  </View>
                  <View style={[
                    styles.simBadge,
                    { backgroundColor: similarity >= 80 ? Colors.successDim : similarity >= 50 ? Colors.accentGlow : Colors.dangerDim }
                  ]}>
                    <Text style={[
                      styles.simText,
                      { color: similarity >= 80 ? Colors.success : similarity >= 50 ? Colors.accent : Colors.danger }
                    ]}>
                      {similarity}%
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        )}

        <TouchableOpacity
          style={styles.unmatchBtn}
          onPress={() => handleUnmatch(p.id)}
          activeOpacity={0.7}
        >
          <Text style={styles.unmatchText}>Unmatch</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Matches</Text>
          <Text style={styles.headerSub}>
            {matches.length} confirmed {matches.length === 1 ? 'match' : 'matches'}
          </Text>
        </View>
        <NotificationBell onPress={() => navigation.navigate('Notifications')} />
      </View>

      {matches.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emoji}>🏠</Text>
          <Text style={styles.emptyTitle}>No Matches Yet</Text>
          <Text style={styles.emptySubtitle}>
            When you and someone like each other, you'll see them here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={matches}
          keyExtractor={(item, i) => `${item._id || i}`}
          renderItem={renderMatch}
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
    borderColor: Colors.success,
  },
  matchBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  matchEmoji: { fontSize: 20 },
  matchLabel: { fontSize: 14, fontWeight: '700', color: Colors.success },
  scorePill: {
    marginLeft: 'auto',
    backgroundColor: Colors.successDim,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: Radius.full,
  },
  scorePillText: { fontSize: 12, fontWeight: '600', color: Colors.success },
  cardBody: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.successDim,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.success,
  },
  avatarText: { fontSize: 24, fontWeight: '800', color: Colors.success },
  cardInfo: { flex: 1 },
  cardName: { fontSize: 20, fontWeight: '700', color: Colors.textPrimary },
  cardId: { fontSize: 12, color: Colors.textMuted, marginTop: 2 },
  comparison: {
    backgroundColor: Colors.bgCardLight,
    borderRadius: Radius.md,
    padding: 16,
    marginBottom: 16,
  },
  compTitle: { fontSize: 13, fontWeight: '700', color: Colors.textSecondary, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.6 },
  compRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  compLabel: { flex: 1, fontSize: 12, color: Colors.textMuted },
  compValues: { flexDirection: 'row', alignItems: 'center', marginRight: 10, gap: 4 },
  compYou: { fontSize: 13, fontWeight: '700', color: Colors.accent },
  compVs: { fontSize: 10, color: Colors.textMuted },
  compThem: { fontSize: 13, fontWeight: '700', color: Colors.info },
  simBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: Radius.full, minWidth: 42, alignItems: 'center' },
  simText: { fontSize: 11, fontWeight: '700' },
  unmatchBtn: {
    borderWidth: 1.5,
    borderColor: Colors.danger,
    borderRadius: Radius.md,
    paddingVertical: 12,
    alignItems: 'center',
  },
  unmatchText: { fontSize: 14, fontWeight: '600', color: Colors.danger },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emoji: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
});