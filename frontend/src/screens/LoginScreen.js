import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { setApiBase } from '../services/api';

export default function LoginScreen({ navigation }) {
  const { login } = useAuth();
  const [userId, setUserId] = useState('');
  const [serverUrl, setServerUrl] = useState('http://172.20.10.2:8000/api');
  const [loading, setLoading] = useState(false);
  const [showServer, setShowServer] = useState(false);

  const handleLogin = async () => {
    const id = parseInt(userId.trim(), 10);
    if (isNaN(id)) {
      Alert.alert('Invalid ID', 'Please enter a valid numeric User ID.');
      return;
    }
    setLoading(true);
    try {
      setApiBase(serverUrl);
      await login(id);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not find user. Check ID and server URL.';
      Alert.alert('Login Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        {/* Brand */}
        <View style={styles.brand}>
          <Text style={styles.logo}>🏠</Text>
          <Text style={styles.title}>RoomMatch</Text>
          <Text style={styles.subtitle}>Find your perfect roommate</Text>
        </View>

        {/* Login Card */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Welcome Back</Text>
          <Text style={styles.cardDesc}>Enter your User ID to sign in</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>User ID</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. 42"
              placeholderTextColor={Colors.textMuted}
              keyboardType="number-pad"
              value={userId}
              onChangeText={setUserId}
              returnKeyType="done"
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator color={Colors.black} />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => navigation.navigate('Signup')}
            activeOpacity={0.7}
          >
            <Text style={styles.secondaryButtonText}>Create Account</Text>
          </TouchableOpacity>
        </View>

        {/* Server Config */}
        <TouchableOpacity
          style={styles.serverToggle}
          onPress={() => setShowServer(!showServer)}
        >
          <Text style={styles.serverToggleText}>
            {showServer ? '▼' : '▸'} Server Settings
          </Text>
        </TouchableOpacity>

        {showServer && (
          <View style={styles.serverCard}>
            <Text style={styles.label}>Backend URL</Text>
            <TextInput
              style={styles.input}
              placeholder="http://192.168.x.x:8000/api"
              placeholderTextColor={Colors.textMuted}
              value={serverUrl}
              onChangeText={(v) => {
                setServerUrl(v);
                setApiBase(v);
              }}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text style={styles.hint}>
              Use your machine's local IP when testing on a physical device
            </Text>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingBottom: 40 },
  brand: { alignItems: 'center', marginTop: 80, marginBottom: 36 },
  logo: { fontSize: 52, marginBottom: 12 },
  title: { fontSize: 34, fontWeight: '800', color: Colors.accent, letterSpacing: 1 },
  subtitle: { fontSize: 15, color: Colors.textSecondary, marginTop: 6 },
  card: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: 24,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 4 },
  cardDesc: { fontSize: 14, color: Colors.textSecondary, marginBottom: 24 },
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
  button: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 4,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { fontSize: 16, fontWeight: '700', color: Colors.black },
  divider: { flexDirection: 'row', alignItems: 'center', marginVertical: 20 },
  dividerLine: { flex: 1, height: 1, backgroundColor: Colors.border },
  dividerText: { marginHorizontal: 14, fontSize: 12, color: Colors.textMuted, fontWeight: '600' },
  secondaryButton: {
    borderWidth: 1.5,
    borderColor: Colors.accent,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: 'center',
  },
  secondaryButtonText: { fontSize: 16, fontWeight: '600', color: Colors.accent },
  serverToggle: { marginTop: 28, alignItems: 'center' },
  serverToggleText: { fontSize: 13, color: Colors.textMuted },
  serverCard: {
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.md,
    padding: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  hint: { fontSize: 11, color: Colors.textMuted, marginTop: 8 },
});
