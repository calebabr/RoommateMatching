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
} from 'react-native';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES } from '../utils/categories';
import { createUser, setApiBase } from '../services/api';
import { useAuth } from '../context/AuthContext';
import SliderPicker from '../components/SliderPicker';

export default function SignupScreen({ navigation }) {
  const { signup } = useAuth();
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0); // 0 = name, 1 = preferences

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

  const handleCreate = async () => {
    if (!username.trim()) {
      Alert.alert('Missing Name', 'Please enter a username.');
      return;
    }
    setLoading(true);
    try {
      const payload = { username: username.trim(), ...preferences };
      const user = await createUser(payload);
      Alert.alert(
        'Account Created!',
        `Welcome ${user.username}! Your ID is ${user.id}. Remember this for logging in.`,
        [{ text: 'OK', onPress: () => signup(user) }]
      );
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not create account.';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => (step === 0 ? navigation.goBack() : setStep(0))}>
          <Text style={styles.backBtn}>← Back</Text>
        </TouchableOpacity>
        <View style={styles.stepIndicator}>
          <View style={[styles.dot, step >= 0 && styles.dotActive]} />
          <View style={[styles.dotLine, step >= 1 && styles.dotLineActive]} />
          <View style={[styles.dot, step >= 1 && styles.dotActive]} />
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {step === 0 ? (
          /* ─── Step 1: Username ─── */
          <View>
            <Text style={styles.title}>Create Your Profile</Text>
            <Text style={styles.subtitle}>
              Let's start with your name
            </Text>
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
            <TouchableOpacity
              style={[styles.button, !username.trim() && styles.buttonDisabled]}
              onPress={() => {
                if (!username.trim()) {
                  Alert.alert('Missing Name', 'Please enter a username.');
                  return;
                }
                setStep(1);
              }}
              disabled={!username.trim()}
              activeOpacity={0.8}
            >
              <Text style={styles.buttonText}>Next — Set Preferences</Text>
            </TouchableOpacity>
          </View>
        ) : (
          /* ─── Step 2: Preferences ─── */
          <View>
            <Text style={styles.title}>Your Preferences</Text>
            <Text style={styles.subtitle}>
              Rate each category and mark deal-breakers
            </Text>

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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: Platform.OS === 'ios' ? 60 : 40,
    paddingBottom: 12,
  },
  backBtn: { fontSize: 16, color: Colors.accent, fontWeight: '600' },
  stepIndicator: { flexDirection: 'row', alignItems: 'center' },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: Colors.border },
  dotActive: { backgroundColor: Colors.accent },
  dotLine: { width: 30, height: 2, backgroundColor: Colors.border, marginHorizontal: 4 },
  dotLineActive: { backgroundColor: Colors.accent },
  scroll: { paddingHorizontal: 24, paddingBottom: 60 },
  title: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary, marginTop: 8, marginBottom: 4 },
  subtitle: { fontSize: 15, color: Colors.textSecondary, marginBottom: 28 },
  inputGroup: { marginBottom: 24 },
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
});
