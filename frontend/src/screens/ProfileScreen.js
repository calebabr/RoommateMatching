import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Switch,
  Platform,
} from 'react-native';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { updateUser, deleteUser } from '../services/api';
import SliderPicker from '../components/SliderPicker';

export default function ProfileScreen() {
  const { user, refreshUser, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [preferences, setPreferences] = useState(
    CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = {
        value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2),
        isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false,
      };
      return acc;
    }, {})
  );

  const updatePref = (key, field, val) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: val },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { username: user.username, ...preferences };
      await updateUser(user.id, payload);
      await refreshUser();
      setEditing(false);
      Alert.alert('Saved', 'Your preferences have been updated.');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not update profile.';
      Alert.alert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = () => {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account, matches, and all data. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteUser(user.id);
              await logout();
            } catch (err) {
              Alert.alert('Error', 'Could not delete account.');
            }
          },
        },
      ]
    );
  };

  if (!user) return null;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
      {/* Profile Header */}
      <View style={styles.profileHeader}>
        <View style={styles.avatarLarge}>
          <Text style={styles.avatarLargeText}>
            {(user.username || '?')[0].toUpperCase()}
          </Text>
        </View>
        <Text style={styles.username}>{user.username}</Text>
        <Text style={styles.userId}>ID: {user.id}</Text>
        <View style={[styles.statusBadge, user.matched ? styles.statusMatched : styles.statusSearching]}>
          <Text style={[styles.statusText, { color: user.matched ? Colors.success : Colors.accent }]}>
            {user.matched ? `Matched with #${user.matchedWith}` : 'Searching for roommate'}
          </Text>
        </View>
      </View>

      {/* Preferences Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Your Preferences</Text>
          {!editing && (
            <TouchableOpacity onPress={() => setEditing(true)}>
              <Text style={styles.editBtn}>Edit</Text>
            </TouchableOpacity>
          )}
        </View>

        {CATEGORIES.map((cat) => {
          const pref = editing ? preferences[cat.key] : user[cat.key];
          if (!pref) return null;

          return (
            <View key={cat.key} style={styles.prefCard}>
              <View style={styles.prefHeader}>
                <Text style={styles.prefLabel}>{cat.label}</Text>
                {pref.isDealBreaker && (
                  <View style={styles.dealBreakerBadge}>
                    <Text style={styles.dealBreakerBadgeText}>Deal-breaker</Text>
                  </View>
                )}
              </View>

              {editing ? (
                <View>
                  <View style={styles.dealBreakerRow}>
                    <Text style={styles.dealBreakerToggleText}>Mark as deal-breaker</Text>
                    <Switch
                      value={preferences[cat.key].isDealBreaker}
                      onValueChange={(v) => updatePref(cat.key, 'isDealBreaker', v)}
                      trackColor={{ false: Colors.border, true: Colors.danger }}
                      thumbColor={preferences[cat.key].isDealBreaker ? Colors.white : Colors.textMuted}
                    />
                  </View>
                  <SliderPicker
                    min={cat.min}
                    max={cat.max}
                    value={preferences[cat.key].value}
                    onChange={(v) => updatePref(cat.key, 'value', v)}
                    formatLabel={cat.formatValue}
                  />
                </View>
              ) : (
                <View style={styles.prefDisplay}>
                  <Text style={styles.prefValue}>{cat.formatValue(pref.value)}</Text>
                  <View style={styles.prefBarTrack}>
                    <View style={[styles.prefBarFill, { width: `${(pref.value / cat.max) * 100}%` }]} />
                  </View>
                </View>
              )}
            </View>
          );
        })}

        {editing && (
          <View style={styles.editActions}>
            <TouchableOpacity
              style={styles.saveBtn}
              onPress={handleSave}
              disabled={saving}
              activeOpacity={0.8}
            >
              {saving ? (
                <ActivityIndicator color={Colors.black} />
              ) : (
                <Text style={styles.saveBtnText}>Save Changes</Text>
              )}
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={() => {
                setEditing(false);
                // Reset to current user values
                setPreferences(
                  CATEGORIES.reduce((acc, cat) => {
                    acc[cat.key] = {
                      value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2),
                      isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false,
                    };
                    return acc;
                  }, {})
                );
              }}
              activeOpacity={0.7}
            >
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Account Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <TouchableOpacity style={styles.logoutBtn} onPress={logout} activeOpacity={0.7}>
          <Text style={styles.logoutBtnText}>Log Out</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.deleteBtn} onPress={handleDelete} activeOpacity={0.7}>
          <Text style={styles.deleteBtnText}>Delete Account</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  scroll: { paddingHorizontal: 24, paddingBottom: 60, paddingTop: 16 },
  profileHeader: { alignItems: 'center', marginBottom: 32 },
  avatarLarge: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: Colors.accentGlow,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: Colors.accent,
    marginBottom: 16,
  },
  avatarLargeText: { fontSize: 36, fontWeight: '800', color: Colors.accent },
  username: { fontSize: 26, fontWeight: '800', color: Colors.textPrimary },
  userId: { fontSize: 14, color: Colors.textMuted, marginTop: 4 },
  statusBadge: {
    marginTop: 12,
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1,
  },
  statusMatched: { backgroundColor: Colors.successDim, borderColor: Colors.success },
  statusSearching: { backgroundColor: Colors.accentGlow, borderColor: Colors.accent },
  statusText: { fontSize: 13, fontWeight: '600' },
  section: { marginBottom: 28 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary },
  editBtn: { fontSize: 15, fontWeight: '600', color: Colors.accent },
  prefCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  prefHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  prefLabel: { fontSize: 15, fontWeight: '600', color: Colors.textPrimary },
  dealBreakerBadge: {
    backgroundColor: Colors.dangerDim,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radius.full,
  },
  dealBreakerBadgeText: { fontSize: 10, fontWeight: '700', color: Colors.danger, textTransform: 'uppercase' },
  dealBreakerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  dealBreakerToggleText: { fontSize: 13, color: Colors.danger },
  prefDisplay: {},
  prefValue: { fontSize: 15, fontWeight: '700', color: Colors.accent, marginBottom: 8 },
  prefBarTrack: { height: 6, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden' },
  prefBarFill: { height: '100%', backgroundColor: Colors.accent, borderRadius: 3 },
  editActions: { marginTop: 8, gap: 10 },
  saveBtn: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
  cancelBtn: {
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  cancelBtnText: { fontSize: 15, fontWeight: '600', color: Colors.textSecondary },
  logoutBtn: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  logoutBtnText: { fontSize: 15, fontWeight: '600', color: Colors.textPrimary },
  deleteBtn: {
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
    borderWidth: 1.5,
    borderColor: Colors.danger,
  },
  deleteBtnText: { fontSize: 15, fontWeight: '600', color: Colors.danger },
});
