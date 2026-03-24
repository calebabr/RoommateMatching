import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Image,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatConversations, getUser, getPhotoUrl } from '../services/api';
import NotificationBell from '../components/NotificationBell';

export default function ChatListScreen() {
  const navigation = useNavigation();
  const { user, refreshUser } = useAuth();
  const insets = useSafeAreaInsets();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!user?.id) return;
    try {
      await refreshUser();
      const convos = await getChatConversations(user.id);
      const enriched = await Promise.all(
        convos.map(async (c) => {
          try {
            const profile = await getUser(c.partnerId);
            return { ...c, profile };
          } catch {
            return { ...c, profile: { id: c.partnerId, username: `User #${c.partnerId}` } };
          }
        })
      );
      setConversations(enriched);
    } catch {
      setConversations([]);
    }
  };

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        setLoading(true);
        await load();
        if (active) setLoading(false);
      })();
      return () => { active = false; };
    }, [user?.id])
  );

  const getTimeStr = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return `${Math.floor(diffH / 24)}d ago`;
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  const renderConversation = ({ item }) => {
    const p = item.profile;
    const photoSrc = getPhotoUrl(p?.photoUrl);
    const lastMsg = item.lastMessage;

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate('ChatRoom', { partnerId: p.id, partnerName: p.username })}
        activeOpacity={0.8}
      >
        {photoSrc ? (
          <Image source={{ uri: photoSrc }} style={styles.avatar} />
        ) : (
          <View style={styles.avatarFallback}>
            <Text style={styles.avatarText}>{(p?.username || '?')[0].toUpperCase()}</Text>
          </View>
        )}
        <View style={styles.cardContent}>
          <View style={styles.cardRow}>
            <Text style={styles.name}>{p?.username || `User #${p?.id}`}</Text>
            {lastMsg && (
              <Text style={styles.time}>{getTimeStr(lastMsg.createdAt)}</Text>
            )}
          </View>
          <Text style={styles.preview} numberOfLines={1}>
            {lastMsg
              ? (lastMsg.fromUser === user.id ? `You: ${lastMsg.content}` : lastMsg.content)
              : 'No messages yet — say hello!'}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { paddingTop: insets.top + 16 }]}>
        <View>
          <Text style={styles.headerTitle}>Chat</Text>
          <Text style={styles.headerSub}>
            {conversations.length} {conversations.length === 1 ? 'conversation' : 'conversations'}
          </Text>
        </View>
        <NotificationBell onPress={() => navigation.navigate('Notifications')} />
      </View>

      {conversations.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emoji}>💬</Text>
          <Text style={styles.emptyTitle}>No Chats Yet</Text>
          <Text style={styles.emptySubtitle}>
            Match with someone to start chatting!
          </Text>
        </View>
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(item) => String(item.partnerId)}
          renderItem={renderConversation}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    paddingHorizontal: 24,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: { fontSize: 28, fontWeight: '800', color: Colors.textPrimary },
  headerSub: { fontSize: 13, color: Colors.textSecondary, marginTop: 2 },
  list: { paddingHorizontal: 16, paddingBottom: 30, paddingTop: 8 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bgCard,
    borderRadius: Radius.lg,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.success,
    backgroundColor: Colors.bgCard,
  },
  avatarFallback: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: Colors.successDim,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
    borderWidth: 2,
    borderColor: Colors.success,
  },
  avatarText: { fontSize: 22, fontWeight: '800', color: Colors.success },
  cardContent: { flex: 1 },
  cardRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  name: { fontSize: 16, fontWeight: '700', color: Colors.textPrimary },
  time: { fontSize: 11, color: Colors.textMuted },
  preview: { fontSize: 13, color: Colors.textSecondary },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40, backgroundColor: Colors.bg },
  emoji: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
});
