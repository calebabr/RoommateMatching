import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  Switch,
  Platform,
  Image,
  KeyboardAvoidingView,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import { createUser, uploadPhoto, getPhotoUrl, setApiBase } from '../services/api';
import { useAuth } from '../context/AuthContext';
import SliderPicker from '../components/SliderPicker';

export default function SignupScreen({ navigation }) {
  const { signup } = useAuth();
  const insets = useSafeAreaInsets();
  const [username, setUsername] = useState('');
  const [gender, setGender] = useState(''); // 'male' or 'female'
  const [bio, setBio] = useState('');
  const [photoUri, setPhotoUri] = useState(null); // local image URI from picker
  const [selectedTags, setSelectedTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0); // 0 = profile+gender, 1 = preferences, 2 = tags

  const [preferences, setPreferences] = useState(
    CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: Math.round((cat.max - cat.min) / 2), isDealBreaker: false };
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
    // Ask for permission
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
      setPhotoUri(result.assets[0].uri);
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
      setPhotoUri(result.assets[0].uri);
    }
  };

  const handleCreate = async () => {
    if (!username.trim()) {
      Alert.alert('Missing Name', 'Please enter a username.');
      return;
    }
    if (!gender) {
      Alert.alert('Missing Gender', 'Please select your gender.');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        username: username.trim(),
        gender: gender,
        bio: bio.trim(),
        lifestyleTags: selectedTags,
        ...preferences,
      };
      const createdUser = await createUser(payload);

      // Upload photo if selected
      if (photoUri) {
        try {
          const photoResult = await uploadPhoto(createdUser.id, photoUri);
          createdUser.photoUrl = photoResult.photoUrl;
        } catch (photoErr) {
          console.warn('Photo upload failed:', photoErr);
          // Account still created, just no photo
        }
      }

      Alert.alert(
        'Account Created!',
        `Welcome ${createdUser.username}! Your ID is ${createdUser.id}. Remember this for logging in.`,
        [{ text: 'OK', onPress: () => signup(createdUser) }]
      );
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not create account.';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  const totalSteps = 3;

  const canProceedStep0 = username.trim() && gender;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <TouchableOpacity onPress={() => (step === 0 ? navigation.goBack() : setStep(step - 1))}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <View style={styles.stepIndicator}>
          {Array.from({ length: totalSteps }).map((_, i) => (
            <React.Fragment key={i}>
              {i > 0 && <View style={[styles.dotLine, step >= i && styles.dotLineActive]} />}
              <View style={[styles.dot, step >= i && styles.dotActive]} />
            </React.Fragment>
          ))}
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {step === 0 ? (
          /* ─── Step 1: Profile Info + Gender ─── */
          <View>
            <Text style={styles.title}>Create Your Profile</Text>
            <Text style={styles.subtitle}>Tell potential roommates about yourself</Text>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Username</Text>
              <TextInput
                style={styles.input}
                placeholder="Enter a unique username"
                placeholderTextColor={Colors.textMuted}
                value={username}
                onChangeText={setUsername}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="next"
              />
            </View>

            {/* Gender Selection */}
            <View style={styles.inputGroup}>
              <Text style={styles.label}>Gender</Text>
              <Text style={styles.genderHint}>
                You'll only be matched with roommates of the same gender
              </Text>
              <View style={styles.genderRow}>
                <TouchableOpacity
                  style={[
                    styles.genderBtn,
                    gender === 'male' && styles.genderBtnSelected,
                  ]}
                  onPress={() => setGender('male')}
                  activeOpacity={0.7}
                >
                  <Text style={styles.genderEmoji}>👨</Text>
                  <Text
                    style={[
                      styles.genderBtnText,
                      gender === 'male' && styles.genderBtnTextSelected,
                    ]}
                  >
                    Male
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[
                    styles.genderBtn,
                    gender === 'female' && styles.genderBtnSelected,
                  ]}
                  onPress={() => setGender('female')}
                  activeOpacity={0.7}
                >
                  <Text style={styles.genderEmoji}>👩</Text>
                  <Text
                    style={[
                      styles.genderBtnText,
                      gender === 'female' && styles.genderBtnTextSelected,
                    ]}
                  >
                    Female
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Bio</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="A short intro — what are you like as a roommate?"
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

            <View style={styles.inputGroup}>
              <Text style={styles.label}>Profile Photo (optional)</Text>
              {photoUri ? (
                <View style={styles.photoPreviewWrap}>
                  <Image source={{ uri: photoUri }} style={styles.photoPreview} />
                  <TouchableOpacity
                    style={styles.photoRemoveBtn}
                    onPress={() => setPhotoUri(null)}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.photoRemoveText}>✕ Remove</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.photoPickerRow}>
                  <TouchableOpacity
                    style={styles.photoPickerBtn}
                    onPress={pickImage}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.photoPickerEmoji}>🖼️</Text>
                    <Text style={styles.photoPickerBtnText}>Choose Photo</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.photoPickerBtn}
                    onPress={takePhoto}
                    activeOpacity={0.7}
                  >
                    <Text style={styles.photoPickerEmoji}>📷</Text>
                    <Text style={styles.photoPickerBtnText}>Take Photo</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>

            <TouchableOpacity
              style={[styles.button, !canProceedStep0 && styles.buttonDisabled]}
              onPress={() => {
                if (!username.trim()) {
                  Alert.alert('Missing Name', 'Please enter a username.');
                  return;
                }
                if (!gender) {
                  Alert.alert('Missing Gender', 'Please select your gender.');
                  return;
                }
                setStep(1);
              }}
              disabled={!canProceedStep0}
              activeOpacity={0.8}
            >
              <Text style={styles.buttonText}>Next — Set Preferences</Text>
            </TouchableOpacity>
          </View>
        ) : step === 1 ? (
          /* ─── Step 2: Preferences ─── */
          <View>
            <Text style={styles.title}>Your Preferences</Text>
            <Text style={styles.subtitle}>Rate each category and mark deal-breakers</Text>

            {CATEGORIES.map((cat) => (
              <View key={cat.key} style={styles.prefCard}>
                <View style={styles.prefHeader}>
                  <Text style={styles.prefLabel}>{cat.label}</Text>
                  <View style={styles.dealBreakerRow}>
                    <Text style={styles.dealBreakerText}>Deal-breaker</Text>
                    <Switch
                      value={preferences[cat.key].isDealBreaker}
                      onValueChange={(v) => updatePref(cat.key, 'isDealBreaker', v)}
                      trackColor={{ false: Colors.border, true: Colors.danger }}
                      thumbColor={preferences[cat.key].isDealBreaker ? Colors.white : Colors.textMuted}
                    />
                  </View>
                </View>
                <Text style={styles.prefDesc}>{cat.description}</Text>
                <SliderPicker
                  min={cat.min}
                  max={cat.max}
                  value={preferences[cat.key].value}
                  onChange={(v) => updatePref(cat.key, 'value', v)}
                  formatLabel={cat.formatValue}
                />
              </View>
            ))}

            <TouchableOpacity
              style={styles.button}
              onPress={() => setStep(2)}
              activeOpacity={0.8}
            >
              <Text style={styles.buttonText}>Next — Lifestyle Tags</Text>
            </TouchableOpacity>
          </View>
        ) : (
          /* ─── Step 3: Lifestyle Tags ─── */
          <View>
            <Text style={styles.title}>Lifestyle Tags</Text>
            <Text style={styles.subtitle}>
              Pick tags that describe you — shared tags boost your match score!
            </Text>

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

            <Text style={styles.tagCount}>
              {selectedTags.length} selected
            </Text>

            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={handleCreate}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color={Colors.black} />
              ) : (
                <Text style={styles.buttonText}>Create Account</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  backBtn: { fontSize: 16, color: Colors.accent, fontWeight: '600' },
  stepIndicator: { flexDirection: 'row', alignItems: 'center' },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: Colors.border },
  dotActive: { backgroundColor: Colors.accent },
  dotLine: { width: 24, height: 2, backgroundColor: Colors.border, marginHorizontal: 4 },
  dotLineActive: { backgroundColor: Colors.accent },
  scroll: { paddingHorizontal: 24, paddingBottom: 60 },
  title: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary, marginTop: 8, marginBottom: 4 },
  subtitle: { fontSize: 15, color: Colors.textSecondary, marginBottom: 28 },
  inputGroup: { marginBottom: 20 },
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
  photoPreviewWrap: { alignItems: 'center', marginTop: 12 },
  photoPreview: { width: 100, height: 100, borderRadius: 50, backgroundColor: Colors.bgCard, borderWidth: 3, borderColor: Colors.accent },
  photoRemoveBtn: { marginTop: 10, paddingHorizontal: 16, paddingVertical: 6, borderRadius: Radius.full, borderWidth: 1, borderColor: Colors.danger },
  photoRemoveText: { fontSize: 13, fontWeight: '600', color: Colors.danger },
  photoPickerRow: { flexDirection: 'row', gap: 12 },
  photoPickerBtn: {
    flex: 1,
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    paddingVertical: 18,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.border,
    borderStyle: 'dashed',
  },
  photoPickerEmoji: { fontSize: 28, marginBottom: 6 },
  photoPickerBtnText: { fontSize: 13, fontWeight: '600', color: Colors.textSecondary },
  genderHint: { fontSize: 12, color: Colors.textMuted, marginBottom: 12, fontStyle: 'italic' },
  genderRow: { flexDirection: 'row', gap: 12 },
  genderBtn: {
    flex: 1,
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    paddingVertical: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: Colors.border,
  },
  genderBtnSelected: {
    borderColor: Colors.accent,
    backgroundColor: Colors.accentGlow,
  },
  genderEmoji: { fontSize: 36, marginBottom: 8 },
  genderBtnText: { fontSize: 16, fontWeight: '700', color: Colors.textSecondary },
  genderBtnTextSelected: { color: Colors.accent },
  button: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 20,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { fontSize: 16, fontWeight: '700', color: Colors.black },
  prefCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  prefHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  prefLabel: { fontSize: 16, fontWeight: '700', color: Colors.textPrimary, flex: 1 },
  prefDesc: { fontSize: 13, color: Colors.textSecondary, marginTop: 4, marginBottom: 16 },
  dealBreakerRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dealBreakerText: { fontSize: 11, color: Colors.danger, fontWeight: '600', textTransform: 'uppercase' },
  tagGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  tagChip: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: Radius.full,
    borderWidth: 1.5,
    borderColor: Colors.border,
    backgroundColor: Colors.bgCard,
  },
  tagChipSelected: {
    borderColor: Colors.accent,
    backgroundColor: Colors.accentGlow,
  },
  tagChipText: { fontSize: 14, fontWeight: '600', color: Colors.textSecondary },
  tagChipTextSelected: { color: Colors.accent },
  tagCount: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', marginBottom: 8 },
});