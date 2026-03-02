import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView,
  TouchableOpacity, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import Button from '../components/Button';
import Avatar from '../components/Avatar';
import PreferenceSlider from '../components/PreferenceSlider';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, SPACING, RADIUS, PREFERENCE_CONFIG } from '../constants/theme';

const TOTAL_STEPS = 4;

const DEFAULT_PREFS = {
  sleepScoreWD: { value: 23, isDealBreaker: false },
  sleepScoreWE: { value: 0, isDealBreaker: false },
  cleanlinessScore: { value: 5, isDealBreaker: false },
  noiseToleranceScore: { value: 5, isDealBreaker: false },
  guestsScore: { value: 5, isDealBreaker: false },
};

export default function RegisterScreen({ navigation }) {
  const { login } = useAuth();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [profilePic, setProfilePic] = useState(null);
  const [bio, setBio] = useState('');
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);

  const progress = ((step + 1) / TOTAL_STEPS) * 100;

  const updatePref = (key, field, value) => {
    setPrefs((p) => ({ ...p, [key]: { ...p[key], [field]: value } }));
  };

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Photo access is required for a profile picture.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });
    if (!result.canceled) setProfilePic(result.assets[0].uri);
  };

  const handleCreate = async () => {
    if (!username.trim()) { Alert.alert('Error', 'Username is required'); return; }
    setLoading(true);
    try {
      const payload = { username: username.trim(), ...prefs };
      const user = await api.createUser(payload);
      login({ ...user, profilePic, bio, password });
    } catch (err) {
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  };

  const canContinue = step === 0 ? username.trim().length > 0 : true;

  // ── Step 0: Account ──
  const StepAccount = () => (
    <View>
      <Text style={s.heading}>Create your account</Text>
      <Text style={s.sub}>Choose a username that represents you</Text>
      <Text style={s.label}>Username *</Text>
      <TextInput style={s.input} value={username} onChangeText={setUsername}
        placeholder="e.g. NightOwlNina" placeholderTextColor={COLORS.textMuted} autoCapitalize="none" />
      <Text style={[s.label, { marginTop: 20 }]}>Password</Text>
      <TextInput style={s.input} value={password} onChangeText={setPassword}
        placeholder="Will be secured later" placeholderTextColor={COLORS.textMuted} secureTextEntry />
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 }}>
        <Feather name="shield" size={12} color={COLORS.textMuted} />
        <Text style={{ color: COLORS.textMuted, fontSize: 11 }}>Full authentication coming soon</Text>
      </View>
    </View>
  );

  // ── Step 1: Photo & Bio ──
  const StepPhoto = () => (
    <View>
      <Text style={s.heading}>Show yourself</Text>
      <Text style={s.sub}>Add a photo and short bio</Text>
      <View style={{ alignItems: 'center', marginBottom: 28 }}>
        <View>
          <Avatar uri={profilePic} name={username} size={120} />
          <TouchableOpacity onPress={pickImage} style={s.cameraBtn}>
            <Feather name="camera" size={16} color="#fff" />
          </TouchableOpacity>
        </View>
        {profilePic ? (
          <TouchableOpacity onPress={() => setProfilePic(null)}>
            <Text style={{ color: COLORS.textDim, fontSize: 12, marginTop: 8 }}>Remove photo</Text>
          </TouchableOpacity>
        ) : (
          <Text style={{ color: COLORS.textDim, fontSize: 12, marginTop: 8, textAlign: 'center' }}>
            A default avatar will be used if no photo is uploaded
          </Text>
        )}
      </View>
      <Text style={s.label}>Short bio</Text>
      <TextInput style={[s.input, { height: 90, textAlignVertical: 'top' }]}
        value={bio} onChangeText={setBio} placeholder="Tell potential roommates about yourself..."
        placeholderTextColor={COLORS.textMuted} multiline maxLength={200} />
      <Text style={{ color: COLORS.textMuted, fontSize: 11, textAlign: 'right', marginTop: 4 }}>{bio.length}/200</Text>
    </View>
  );

  // ── Step 2: Sleep & Cleanliness ──
  const StepPrefs1 = () => (
    <View>
      <Text style={s.heading}>Your lifestyle</Text>
      <Text style={s.sub}>Rate your preferences — toggle dealbreaker for must-haves</Text>
      {['sleepScoreWD', 'sleepScoreWE', 'cleanlinessScore'].map((key) => {
        const cfg = PREFERENCE_CONFIG[key];
        return (
          <PreferenceSlider key={key} label={cfg.label} description={cfg.description}
            icon={cfg.icon} value={prefs[key].value} min={cfg.min} max={cfg.max}
            isDealBreaker={prefs[key].isDealBreaker}
            onValueChange={(v) => updatePref(key, 'value', v)}
            onDealBreakerChange={(v) => updatePref(key, 'isDealBreaker', v)} />
        );
      })}
    </View>
  );

  // ── Step 3: Noise, Guests & Summary ──
  const StepPrefs2 = () => (
    <View>
      <Text style={s.heading}>Almost there</Text>
      <Text style={s.sub}>A couple more preferences, then you're set</Text>
      {['noiseToleranceScore', 'guestsScore'].map((key) => {
        const cfg = PREFERENCE_CONFIG[key];
        return (
          <PreferenceSlider key={key} label={cfg.label} description={cfg.description}
            icon={cfg.icon} value={prefs[key].value} min={cfg.min} max={cfg.max}
            isDealBreaker={prefs[key].isDealBreaker}
            onValueChange={(v) => updatePref(key, 'value', v)}
            onDealBreakerChange={(v) => updatePref(key, 'isDealBreaker', v)} />
        );
      })}
      <View style={s.summary}>
        <Text style={{ color: COLORS.accentSoft, fontSize: 16, fontWeight: '700', marginBottom: 12 }}>Profile Summary</Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 14 }}>
          <Avatar uri={profilePic} name={username} size={40} />
          <View style={{ marginLeft: 12 }}>
            <Text style={{ color: COLORS.text, fontWeight: '700', fontSize: 15 }}>{username || 'No username'}</Text>
            <Text style={{ color: COLORS.textDim, fontSize: 12 }}>{bio || 'No bio yet'}</Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          {Object.entries(PREFERENCE_CONFIG).map(([key, cfg]) => (
            <View key={key} style={s.summaryItem}>
              <Text style={s.summaryLabel}>{cfg.label.split(' ')[0]}</Text>
              <Text style={s.summaryVal}>{prefs[key].value}{cfg.unit}</Text>
            </View>
          ))}
        </View>
      </View>
    </View>
  );

  const steps = [StepAccount, StepPhoto, StepPrefs1, StepPrefs2];
  const CurrentStep = steps[step];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: COLORS.bg }}>
      <View style={s.progressRow}>
        <TouchableOpacity onPress={() => step > 0 ? setStep(step - 1) : navigation.goBack()}>
          <Feather name="chevron-left" size={24} color={COLORS.text} />
        </TouchableOpacity>
        <View style={s.progressTrack}>
          <View style={[s.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={{ color: COLORS.textDim, fontSize: 12, fontWeight: '600' }}>{step + 1}/{TOTAL_STEPS}</Text>
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 28, paddingTop: 8, paddingBottom: 20 }}
        keyboardShouldPersistTaps="handled">
        <CurrentStep />
      </ScrollView>

      <View style={{ paddingHorizontal: 28, paddingBottom: 28, paddingTop: 12 }}>
        {step < TOTAL_STEPS - 1 ? (
          <Button title="Continue" onPress={() => setStep(step + 1)} disabled={!canContinue} />
        ) : (
          <Button title="Create Profile" onPress={handleCreate} loading={loading} />
        )}
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  progressRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACING.lg, paddingVertical: 12, gap: 12 },
  progressTrack: { flex: 1, height: 4, backgroundColor: COLORS.surfaceAlt, borderRadius: 2 },
  progressFill: { height: '100%', backgroundColor: COLORS.accent, borderRadius: 2 },
  heading: { fontSize: 26, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  sub: { color: COLORS.textDim, fontSize: 14, lineHeight: 20, marginBottom: 28 },
  label: { color: COLORS.textDim, fontSize: 13, fontWeight: '500', marginBottom: 6 },
  input: {
    backgroundColor: COLORS.surfaceAlt, borderWidth: 1.5, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 14, color: COLORS.text, fontSize: 15,
  },
  cameraBtn: {
    position: 'absolute', bottom: 0, right: 0, width: 36, height: 36, borderRadius: 18,
    backgroundColor: COLORS.accent, borderWidth: 3, borderColor: COLORS.bg,
    alignItems: 'center', justifyContent: 'center',
  },
  summary: { backgroundColor: COLORS.surfaceAlt, borderRadius: RADIUS.md, padding: 20, marginTop: 8 },
  summaryItem: { backgroundColor: COLORS.card, borderRadius: 8, padding: 10, width: '48%' },
  summaryLabel: { fontSize: 10, color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: 0.8 },
  summaryVal: { fontSize: 14, fontWeight: '700', color: COLORS.accent, marginTop: 2 },
});
