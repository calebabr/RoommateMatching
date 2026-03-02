import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, Alert,
  KeyboardAvoidingView, Platform, TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import Button from '../components/Button';
import { useAuth } from '../hooks/useAuth';
import * as api from '../services/api';
import { COLORS, SPACING, RADIUS } from '../constants/theme';

export default function LoginScreen({ navigation }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username.trim()) return;
    setLoading(true);
    try {
      const users = await api.getAllUsers();
      const found = users.find(
        (u) => u.username.toLowerCase() === username.trim().toLowerCase()
      );
      if (found) {
        login(found);
      } else {
        Alert.alert('Not Found', 'No account with that username.');
      }
    } catch (err) {
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.inner}
      >
        <TouchableOpacity onPress={() => navigation.goBack()} style={{ marginBottom: SPACING.lg, alignSelf: 'flex-start' }}>
          <Feather name="chevron-left" size={28} color={COLORS.text} />
        </TouchableOpacity>

        <Text style={styles.heading}>Welcome back</Text>
        <Text style={styles.sub}>Sign in to your account</Text>

        <Text style={styles.label}>Username</Text>
        <TextInput
          style={styles.input}
          value={username}
          onChangeText={setUsername}
          placeholder="Enter username"
          placeholderTextColor={COLORS.textMuted}
          autoCapitalize="none"
        />

        <Text style={[styles.label, { marginTop: 20 }]}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="Enter password"
          placeholderTextColor={COLORS.textMuted}
          secureTextEntry
        />

        <View style={{ flex: 1 }} />

        <Button title="Sign In" onPress={handleLogin} disabled={!username.trim()} loading={loading} />
        <Text style={styles.note}>Authentication coming soon — password stored locally for now</Text>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  inner: { flex: 1, paddingHorizontal: SPACING.xl, paddingTop: 12, paddingBottom: SPACING.xl },
  heading: { fontSize: 28, fontWeight: '700', color: COLORS.text, marginBottom: 8 },
  sub: { color: COLORS.textDim, fontSize: 14, marginBottom: SPACING.xl },
  label: { color: COLORS.textDim, fontSize: 13, fontWeight: '500', marginBottom: 6 },
  input: {
    backgroundColor: COLORS.surfaceAlt, borderWidth: 1.5, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 14, color: COLORS.text, fontSize: 15,
  },
  note: { textAlign: 'center', color: COLORS.textMuted, fontSize: 12, marginTop: 16 },
});
