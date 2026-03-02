import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import Button from '../components/Button';
import { COLORS, SPACING } from '../constants/theme';

export default function WelcomeScreen({ navigation }) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.circleTR} />
        <View style={styles.circleBL} />

        <Feather name="zap" size={48} color={COLORS.accent} style={{ marginBottom: 16 }} />

        <Text style={styles.title}>
          Room<Text style={{ color: COLORS.accent }}>Match</Text>
        </Text>

        <Text style={styles.subtitle}>
          Find your ideal roommate based on lifestyle compatibility
        </Text>

        <View style={styles.buttons}>
          <Button title="Create Profile" onPress={() => navigation.navigate('Register')} />
          <Button
            title="Sign In"
            variant="secondary"
            onPress={() => navigation.navigate('Login')}
            style={{ marginTop: 14 }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: SPACING.xl },
  circleTR: {
    position: 'absolute', top: -80, right: -80,
    width: 250, height: 250, borderRadius: 125,
    backgroundColor: COLORS.accentGlow, opacity: 0.4,
  },
  circleBL: {
    position: 'absolute', bottom: -60, left: -60,
    width: 200, height: 200, borderRadius: 100,
    backgroundColor: 'rgba(94,206,123,0.15)', opacity: 0.4,
  },
  title: { fontSize: 38, fontWeight: '700', color: COLORS.text, textAlign: 'center' },
  subtitle: { color: COLORS.textDim, fontSize: 15, textAlign: 'center', lineHeight: 22, marginTop: 16, maxWidth: 280 },
  buttons: { width: '100%', marginTop: 40 },
});
