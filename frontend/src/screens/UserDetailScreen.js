import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { getUser, getMatchScore, sendLike } from '../services/api';

export default function UserDetailScreen({ route, navigation }) {
  const { userId, score: passedScore } = route.params;
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [score, setScore] = useState(passedScore ?? null);
  const [loading, setLoading] = useState(true);
  const [liking, setLiking] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const p = await getUser(userId);
        setProfile(p);
        if (score == null && user?.id) {
          try {
            const s = await getMatchScore(user.id, userId);
            setScore(s.compatibilityScore);
          } catch {}
        }
      } catch {
        Alert.alert('Error', 'Could not load user profile.');
        navigation.goBack();
      } finally {
        setLoading(false);
      }
    })();
  }, [userId]);

  const handleLike = async () => {
    setLiking(true);
    try {
      const result = await sendLike(user.id, userId);
      if (result.status === 'matched') {
        Alert.alert('🎉 Match!', `You and ${profile?.username || 'this user'} are now roommate matches!`);
      } else {
        Alert.alert('Like Sent!', 'They\'ll see your interest.');
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send like.';
      Alert.alert('Error', msg);
    } finally {
      setLiking(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  if (!profile) return null;

  const color = score != null ? getCompatibilityColor(score) : Colors.textMuted;
  const label = score != null ? getCompatibilityLabel(score) : '';

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Avatar & Name */}
        <View style={styles.profileHeader}>
          <View style={[styles.avatar, { borderColor: color }]}>
            <Text style={[styles.avatarText, { color }]}>
              {(profile.username || '?')[0].toUpperCase()}
            </Text>
          </View>
          <Text style={styles.username}>{profile.username}</Text>
          <Text style={styles.userId}>User ID: {profile.id}</Text>

          {/* Status */}
          {profile.matched && (
            <View style={styles.matchedBadge}>
              <Text style={styles.matchedBadgeText}>Currently Matched</Text>
            </View>
          )}

          {/* Score */}
          {score != null && (
            <View style={[styles.scoreBanner, { backgroundColor: color + '15', borderColor: color }]}>
              <Text style={[styles.scoreValue, { color }]}>{Math.round(score * 100)}%</Text>
              <Text style={[styles.scoreDesc, { color }]}>Compatibility — {label}</Text>
            </View>
          )}
        </View>

        {/* Preferences Detail */}
        <Text style={styles.sectionTitle}>Preferences</Text>
        {CATEGORIES.map((cat) => {
          const pref = profile[cat.key];
          if (!pref) return null;
          const myPref = user?.[cat.key];
          const pct = (pref.value / cat.max) * 100;

          return (
            <View key={cat.key} style={styles.prefCard}>
              <View style={styles.prefHeader}>
                <Text style={styles.prefLabel}>{cat.label}</Text>
                {pref.isDealBreaker && (
                  <View style={styles.dbBadge}>
                    <Text style={styles.dbBadgeText}>Deal-breaker</Text>
                  </View>
                )}
              </View>
              <Text style={styles.prefValueText}>{cat.formatValue(pref.value)}</Text>
              <View style={styles.barContainer}>
                <View style={styles.barTrack}>
                  <View style={[styles.barFill, { width: `${pct}%` }]} />
                </View>
              </View>

              {/* Comparison with your score */}
              {myPref && (
                <View style={styles.compRow}>
                  <Text style={styles.compLabel}>You: {cat.formatValue(myPref.value)}</Text>
                  <Text style={styles.compDiff}>
                    Diff: {Math.abs(Math.round(pref.value - myPref.value))}
                  </Text>
                </View>
              )}
            </View>
          );
        })}

        {/* Like Button (only if not already matched and not viewing self) */}
        {!profile.matched && profile.id !== user?.id && !user?.matched && (
          <TouchableOpacity
            style={styles.likeBtn}
            onPress={handleLike}
            disabled={liking}
            activeOpacity={0.8}
          >
            {liking ? (
              <ActivityIndicator color={Colors.black} />
            ) : (
              <Text style={styles.likeBtnText}>♥ Send Like</Text>
            )}
          </TouchableOpacity>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  centered: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center' },
  header: {
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    paddingBottom: 8,
  },
  backBtn: { fontSize: 16, color: Colors.accent, fontWeight: '600' },
  scroll: { paddingHorizontal: 24, paddingBottom: 60 },
  profileHeader: { alignItems: 'center', marginBottom: 28 },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.bgCard,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    marginBottom: 14,
  },
  avatarText: { fontSize: 40, fontWeight: '800' },
  username: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary },
  userId: { fontSize: 13, color: Colors.textMuted, marginTop: 4 },
  matchedBadge: {
    marginTop: 10,
    backgroundColor: Colors.infoDim,
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: Radius.full,
  },
  matchedBadgeText: { fontSize: 12, fontWeight: '600', color: Colors.info },
  scoreBanner: {
    marginTop: 16,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: Radius.lg,
    borderWidth: 1,
    alignItems: 'center',
    width: '100%',
  },
  scoreValue: { fontSize: 36, fontWeight: '800' },
  scoreDesc: { fontSize: 14, fontWeight: '600', marginTop: 2 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary, marginBottom: 14 },
  prefCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  prefHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  prefLabel: { fontSize: 14, fontWeight: '600', color: Colors.textPrimary },
  dbBadge: { backgroundColor: Colors.dangerDim, paddingHorizontal: 8, paddingVertical: 2, borderRadius: Radius.full },
  dbBadgeText: { fontSize: 10, fontWeight: '700', color: Colors.danger, textTransform: 'uppercase' },
  prefValueText: { fontSize: 15, fontWeight: '700', color: Colors.accent, marginBottom: 8 },
  barContainer: { marginBottom: 8 },
  barTrack: { height: 6, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden' },
  barFill: { height: '100%', backgroundColor: Colors.accent, borderRadius: 3 },
  compRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  compLabel: { fontSize: 12, color: Colors.textMuted },
  compDiff: { fontSize: 12, color: Colors.textSecondary, fontWeight: '600' },
  likeBtn: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 20,
  },
  likeBtnText: { fontSize: 16, fontWeight: '700', color: Colors.black },
});
