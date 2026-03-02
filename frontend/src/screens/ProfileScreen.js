import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import Avatar from '../components/Avatar';
import Button from '../components/Button';
import PreferenceSlider from '../components/PreferenceSlider';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, SPACING, RADIUS, PREFERENCE_CONFIG } from '../constants/theme';

export default function ProfileScreen() {
  const { user, updateUser, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [prefs, setPrefs] = useState({
    sleepScoreWD: user?.sleepScoreWD || { value: 5, isDealBreaker: false },
    sleepScoreWE: user?.sleepScoreWE || { value: 5, isDealBreaker: false },
    cleanlinessScore: user?.cleanlinessScore || { value: 5, isDealBreaker: false },
    noiseToleranceScore: user?.noiseToleranceScore || { value: 5, isDealBreaker: false },
    guestsScore: user?.guestsScore || { value: 5, isDealBreaker: false },
  });

  const updatePref = (key, field, value) => {
    setPrefs((p) => ({ ...p, [key]: { ...p[key], [field]: value } }));
  };

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'], allowsEditing: true, aspect: [1, 1], quality: 0.7,
    });
    if (!result.canceled) updateUser({ profilePic: result.assets[0].uri });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { username: user.username, ...prefs };
      const result = await api.updateProfile(user.id, payload);
      updateUser({ ...result });
      setEditing(false);
      Alert.alert('Saved', 'Your preferences have been updated.');
    } catch (e) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', onPress: logout },
    ]);
  };

  const handleDelete = () => {
    Alert.alert('Delete Account',
      'This will permanently delete your profile, matches, and likes. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete', style: 'destructive',
          onPress: async () => {
            try { await api.deleteUser(user.id); logout(); }
            catch (e) { Alert.alert('Error', e.message); }
          },
        },
      ]
    );
  };

  const PrefRow = ({ prefKey }) => {
    const cfg = PREFERENCE_CONFIG[prefKey];
    const pref = user?.[prefKey] || { value: 0, isDealBreaker: false };
    return (
      <View style={st.prefRow}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Feather name={cfg.icon} size={16} color={COLORS.accent} />
          <Text style={{ color: COLORS.text, fontSize: 14 }}>{cfg.label}</Text>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Text style={{ color: COLORS.accent, fontWeight: '700', fontSize: 14 }}>{pref.value}</Text>
          {pref.isDealBreaker && (
            <View style={st.dbBadge}><Text style={st.dbText}>DB</Text></View>
          )}
        </View>
      </View>
    );
  };

  return (
    <ScrollView style={st.container} contentContainerStyle={{ padding: 20, paddingBottom: 40 }}>
      {/* Header */}
      <View style={{ alignItems: 'center', marginBottom: 24 }}>
        <View>
          <Avatar uri={user?.profilePic} name={user?.username} size={100} />
          {editing && (
            <TouchableOpacity style={st.cameraBtn} onPress={pickImage}>
              <Feather name="camera" size={14} color="#fff" />
            </TouchableOpacity>
          )}
        </View>
        <Text style={st.username}>{user?.username}</Text>
        <Text style={{ color: COLORS.textDim, fontSize: 13, marginTop: 4 }}>ID: {user?.id}</Text>
        {user?.bio && <Text style={{ color: COLORS.textDim, fontSize: 14, marginTop: 8, textAlign: 'center' }}>{user.bio}</Text>}
      </View>

      {/* Stats */}
      <View style={{ flexDirection: 'row', gap: 12, marginBottom: 24 }}>
        {[
          ['Matched', user?.matched ? 'Yes' : 'No', user?.matched ? COLORS.green : COLORS.textDim],
          ['User ID', String(user?.id || '-'), COLORS.accent],
        ].map(([label, val, color]) => (
          <View key={label} style={st.statBox}>
            <Text style={{ fontSize: 20, fontWeight: '700', color }}>{val}</Text>
            <Text style={st.statLabel}>{label}</Text>
          </View>
        ))}
      </View>

      {/* Preferences */}
      {!editing ? (
        <View style={st.section}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Text style={st.sectionTitle}>Preferences</Text>
            <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} onPress={() => setEditing(true)}>
              <Feather name="edit-2" size={14} color={COLORS.accent} />
              <Text style={{ color: COLORS.accent, fontSize: 13, fontWeight: '600' }}>Edit</Text>
            </TouchableOpacity>
          </View>
          {Object.keys(PREFERENCE_CONFIG).map((k) => <PrefRow key={k} prefKey={k} />)}
        </View>
      ) : (
        <View style={st.section}>
          <Text style={st.sectionTitle}>Edit Preferences</Text>
          {Object.entries(PREFERENCE_CONFIG).map(([key, cfg]) => (
            <PreferenceSlider key={key} label={cfg.label} description={cfg.description}
              icon={cfg.icon} value={prefs[key].value} min={cfg.min} max={cfg.max}
              isDealBreaker={prefs[key].isDealBreaker}
              onValueChange={(v) => updatePref(key, 'value', v)}
              onDealBreakerChange={(v) => updatePref(key, 'isDealBreaker', v)} />
          ))}
          <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
            <Button title="Cancel" variant="secondary" onPress={() => setEditing(false)} style={{ flex: 1 }} />
            <Button title="Save" onPress={handleSave} loading={saving} style={{ flex: 1 }} />
          </View>
        </View>
      )}

      {/* Account actions */}
      {!editing && (
        <View style={{ gap: 12, marginTop: 8 }}>
          <Button title="Sign Out" variant="secondary" onPress={handleSignOut}
            icon={<Feather name="log-out" size={16} color={COLORS.accent} />} />
          <Button title="Delete Account" variant="danger" onPress={handleDelete}
            icon={<Feather name="trash-2" size={16} color={COLORS.red} />} />
        </View>
      )}
    </ScrollView>
  );
}

const st = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  cameraBtn: {
    position: 'absolute', bottom: 0, right: 0, width: 32, height: 32, borderRadius: 16,
    backgroundColor: COLORS.accent, borderWidth: 2, borderColor: COLORS.bg,
    alignItems: 'center', justifyContent: 'center',
  },
  username: { fontSize: 24, fontWeight: '700', color: COLORS.text, marginTop: 12 },
  statBox: { flex: 1, backgroundColor: COLORS.card, borderRadius: RADIUS.sm, padding: 14, alignItems: 'center' },
  statLabel: { fontSize: 11, color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: 0.8, marginTop: 2 },
  section: { backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: 20, marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text },
  prefRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border,
  },
  dbBadge: { backgroundColor: 'rgba(232,90,90,0.15)', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  dbText: { color: COLORS.red, fontSize: 10, fontWeight: '600' },
});
