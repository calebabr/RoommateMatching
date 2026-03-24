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
  TextInput,
  Image,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { useNavigation } from '@react-navigation/native';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { updateUser, deleteUser, uploadPhoto, getPhotoUrl } from '../services/api';
import SliderPicker from '../components/SliderPicker';
import NotificationBell from '../components/NotificationBell';

export default function ProfileScreen() {
  const navigation = useNavigation();
  const { user, refreshUser, logout } = useAuth();
  const insets = useSafeAreaInsets();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [bio, setBio] = useState(user?.bio || '');
  const [newPhotoUri, setNewPhotoUri] = useState(null); // local URI from picker during edit
  const [selectedTags, setSelectedTags] = useState(user?.lifestyleTags || []);

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

  const toggleTag = (tag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Needed', 'Please allow photo library access to upload a profile picture.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });
    if (!result.canceled && result.assets?.[0]?.uri) {
      setNewPhotoUri(result.assets[0].uri);
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Needed', 'Please allow camera access to take a profile picture.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });
    if (!result.canceled && result.assets?.[0]?.uri) {
      setNewPhotoUri(result.assets[0].uri);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        username: user.username,
        gender: user.gender || 'male',
        bio: bio.trim(),
        lifestyleTags: selectedTags,
        ...preferences,
      };
      await updateUser(user.id, payload);

      // Upload new photo if selected
      if (newPhotoUri) {
        try {
          await uploadPhoto(user.id, newPhotoUri);
        } catch (photoErr) {
          console.warn('Photo upload failed:', photoErr);
        }
      }

      await refreshUser();
      setEditing(false);
      setNewPhotoUri(null);
      Alert.alert('Saved', 'Your profile has been updated.');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not update profile.';
      Alert.alert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setNewPhotoUri(null);
    setBio(user?.bio || '');
    setSelectedTags(user?.lifestyleTags || []);
    setPreferences(
      CATEGORIES.reduce((acc, cat) => {
        acc[cat.key] = {
          value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2),
          isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false,
        };
        return acc;
      }, {})
    );
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
            } catch {
              Alert.alert('Error', 'Could not delete account.');
            }
          },
        },
      ]
    );
  };

  if (!user) return null;

  const displayTags = editing ? selectedTags : (user.lifestyleTags || []);
  const displayBio = editing ? bio : (user.bio || '');
  const genderLabel = user.gender === 'female' ? '♀ Female' : user.gender === 'male' ? '♂ Male' : '';

  // For display: if editing and a new photo was picked, show that; otherwise show existing
  const displayPhotoUri = editing && newPhotoUri
    ? newPhotoUri
    : getPhotoUrl(user.photoUrl);

  return (
    <ScrollView style={styles.container} contentContainerStyle={[styles.scroll, { paddingTop: insets.top + 16 }]} showsVerticalScrollIndicator={false}>
      {/* Top bar with notification bell */}
      <View style={styles.topBar}>
        <Text style={styles.topBarTitle}>Profile</Text>
        <NotificationBell onPress={() => navigation.navigate('Notifications')} />
      </View>

      {/* Profile Header */}
      <View style={styles.profileHeader}>
        {displayPhotoUri ? (
          <Image source={{ uri: displayPhotoUri }} style={styles.avatarImage} />
        ) : (
          <View style={styles.avatarLarge}>
            <Text style={styles.avatarLargeText}>
              {(user.username || '?')[0].toUpperCase()}
            </Text>
          </View>
        )}

        {/* Photo change buttons when editing */}
        {editing && (
          <View style={styles.photoEditRow}>
            <TouchableOpacity style={styles.photoEditBtn} onPress={pickImage} activeOpacity={0.7}>
              <Text style={styles.photoEditBtnText}>🖼️ Gallery</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.photoEditBtn} onPress={takePhoto} activeOpacity={0.7}>
              <Text style={styles.photoEditBtnText}>📷 Camera</Text>
            </TouchableOpacity>
            {(newPhotoUri || user.photoUrl) && (
              <TouchableOpacity
                style={styles.photoRemoveBtn}
                onPress={() => setNewPhotoUri(null)}
                activeOpacity={0.7}
              >
                <Text style={styles.photoRemoveText}>✕</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        <Text style={styles.username}>{user.username}</Text>
        <Text style={styles.userId}>ID: {user.id}</Text>

        {genderLabel !== '' && (
          <View style={styles.genderBadge}>
            <Text style={styles.genderBadgeText}>{genderLabel}</Text>
          </View>
        )}

        {displayBio !== '' && (
          <Text style={styles.bioText}>{displayBio}</Text>
        )}

        {displayTags.length > 0 && (
          <View style={styles.tagRow}>
            {displayTags.map((tag) => (
              <View key={tag} style={styles.tagPill}>
                <Text style={styles.tagPillText}>{tag}</Text>
              </View>
            ))}
          </View>
        )}

        <View style={[styles.statusBadge, user.matched ? styles.statusMatched : styles.statusSearching]}>
          <Text style={[styles.statusText, { color: user.matched ? Colors.success : Colors.accent }]}>
            {user.matched ? `Matched with #${user.matchedWith}` : 'Searching for roommate'}
          </Text>
        </View>
      </View>

      {/* Bio Edit (when editing) */}
      {editing && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Profile Info</Text>
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Bio</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="A short intro about yourself..."
              placeholderTextColor={Colors.textMuted}
              value={bio}
              onChangeText={setBio}
              multiline
              numberOfLines={3}
              maxLength={200}
              textAlignVertical="top"
            />
            <Text style={styles.charCount}>{bio.length}/200</Text>
          </View>
        </View>
      )}

      {/* Lifestyle Tags Edit (when editing) */}
      {editing && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Lifestyle Tags</Text>
          <View style={styles.tagGrid}>
            {LIFESTYLE_TAGS.map((tag) => {
              const selected = selectedTags.includes(tag);
              return (
                <TouchableOpacity
                  key={tag}
                  style={[styles.tagChip, selected && styles.tagChipSelected]}
                  onPress={() => toggleTag(tag)}
                  activeOpacity={0.7}
                >
                  <Text style={[styles.tagChipText, selected && styles.tagChipTextSelected]}>
                    {tag}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      )}

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
                  <View style={styles.dealBreakerToggleRow}>
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
            <TouchableOpacity style={styles.cancelBtn} onPress={handleCancel} activeOpacity={0.7}>
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
  scroll: { paddingHorizontal: 24, paddingBottom: 60 },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  topBarTitle: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary },
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
  avatarImage: {
    width: 88,
    height: 88,
    borderRadius: 44,
    borderWidth: 3,
    borderColor: Colors.accent,
    marginBottom: 16,
    backgroundColor: Colors.bgCard,
  },
  photoEditRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  photoEditBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.accent,
    backgroundColor: Colors.accentGlow,
  },
  photoEditBtnText: { fontSize: 13, fontWeight: '600', color: Colors.accent },
  photoRemoveBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    borderWidth: 1,
    borderColor: Colors.danger,
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoRemoveText: { fontSize: 14, fontWeight: '700', color: Colors.danger },
  username: { fontSize: 26, fontWeight: '800', color: Colors.textPrimary },
  userId: { fontSize: 14, color: Colors.textMuted, marginTop: 4 },
  genderBadge: {
    marginTop: 8,
    backgroundColor: Colors.infoDim,
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.info,
  },
  genderBadgeText: { fontSize: 13, fontWeight: '600', color: Colors.info },
  bioText: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', marginTop: 10, lineHeight: 20, paddingHorizontal: 12 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginTop: 12 },
  tagPill: {
    backgroundColor: Colors.accentGlow,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: Colors.accent,
  },
  tagPillText: { fontSize: 12, fontWeight: '600', color: Colors.accent },
  statusBadge: {
    marginTop: 14,
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
  sectionTitle: { fontSize: 18, fontWeight: '700', color: Colors.textPrimary, marginBottom: 14 },
  editBtn: { fontSize: 15, fontWeight: '600', color: Colors.accent },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '600', color: Colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.8 },
  input: {
    backgroundColor: Colors.bgInput,
    borderRadius: Radius.md,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  textArea: { minHeight: 80, paddingTop: 14 },
  charCount: { fontSize: 11, color: Colors.textMuted, textAlign: 'right', marginTop: 4 },
  tagGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tagChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: Radius.full,
    borderWidth: 1.5,
    borderColor: Colors.border,
    backgroundColor: Colors.bgCard,
  },
  tagChipSelected: { borderColor: Colors.accent, backgroundColor: Colors.accentGlow },
  tagChipText: { fontSize: 13, fontWeight: '600', color: Colors.textSecondary },
  tagChipTextSelected: { color: Colors.accent },
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
  dealBreakerToggleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
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