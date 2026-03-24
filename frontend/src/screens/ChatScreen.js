import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Image,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatMessages, sendChatMessage, getUser, getPhotoUrl, unmatchUser } from '../services/api';

export default function ChatScreen({ navigation, route }) {
  const { partnerId, partnerName } = route.params || {};
  const { user, refreshUser } = useAuth();
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState([]);
  const [partner, setPartner] = useState(partnerName ? { id: partnerId, username: partnerName } : null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const flatListRef = useRef(null);
  const pollRef = useRef(null);

  const loadMessages = async () => {
    if (!user?.id || !partnerId) return;
    try {
      const msgs = await getChatMessages(user.id, partnerId);
      setMessages(msgs);
    } catch {}
  };

  const loadPartner = async () => {
    if (!partnerId) return;
    try {
      const p = await getUser(partnerId);
      setPartner(p);
    } catch {
      setPartner({ id: partnerId, username: partnerName || `User #${partnerId}` });
    }
  };

  useFocusEffect(
    useCallback(() => {
      let active = true;
      (async () => {
        setLoading(true);
        await loadPartner();
        await loadMessages();
        if (active) setLoading(false);
      })();
      pollRef.current = setInterval(() => {
        if (active) loadMessages();
      }, 3000);
      return () => {
        active = false;
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }, [user?.id, partnerId])
  );

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setSending(true);
    setInput('');
    try {
      await sendChatMessage(user.id, partnerId, text);
      await loadMessages();
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send message.';
      Alert.alert('Error', msg);
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  const handleUnmatch = () => {
    Alert.alert(
      'Unmatch',
      `Are you sure you want to unmatch with ${partner?.username || 'this user'}? You'll both return to the matching pool.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unmatch',
          style: 'destructive',
          onPress: async () => {
            try {
              await unmatchUser(user.id, partnerId);
              await refreshUser();
              navigation.goBack();
            } catch (err) {
              Alert.alert('Error', err?.response?.data?.detail || 'Could not unmatch.');
            }
          },
        },
      ]
    );
  };

  const getTimeStr = (dateStr) => {
    const d = new Date(dateStr);
    const h = d.getHours();
    const m = d.getMinutes().toString().padStart(2, '0');
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${h12}:${m} ${ampm}`;
  };

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.accent} />
      </View>
    );
  }

  const partnerPhoto = getPhotoUrl(partner?.photoUrl);

  const renderMessage = ({ item }) => {
    const isMe = item.fromUser === user.id;
    return (
      <View style={[styles.msgRow, isMe && styles.msgRowMe]}>
        <View style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleThem]}>
          <Text style={[styles.bubbleText, isMe ? styles.bubbleTextMe : styles.bubbleTextThem]}>
            {item.content}
          </Text>
          <Text style={[styles.timeText, isMe ? styles.timeTextMe : styles.timeTextThem]}>
            {getTimeStr(item.createdAt)}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Header is OUTSIDE KeyboardAvoidingView so it stays fixed */}
      <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()} activeOpacity={0.7}>
          <Text style={styles.backBtnText}>←</Text>
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          {partnerPhoto ? (
            <Image source={{ uri: partnerPhoto }} style={styles.partnerAvatarImg} />
          ) : (
            <View style={styles.partnerAvatar}>
              <Text style={styles.partnerAvatarText}>
                {(partner?.username || '?')[0].toUpperCase()}
              </Text>
            </View>
          )}
          <View>
            <Text style={styles.partnerName}>{partner?.username || 'Roommate'}</Text>
            <Text style={styles.partnerStatus}>Matched roommate</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.unmatchBtn} onPress={handleUnmatch} activeOpacity={0.7}>
          <Text style={styles.unmatchBtnText}>Unmatch</Text>
        </TouchableOpacity>
      </View>

      {/* KeyboardAvoidingView only wraps messages + input */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {messages.length === 0 ? (
          <View style={styles.emptyChat}>
            <Text style={styles.emptyChatEmoji}>👋</Text>
            <Text style={styles.emptyChatTitle}>Say hello!</Text>
            <Text style={styles.emptyChatSub}>Start the conversation with your new roommate.</Text>
          </View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            renderItem={renderMessage}
            contentContainerStyle={styles.messagesList}
            showsVerticalScrollIndicator={false}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
          />
        )}

        <View style={styles.inputBar}>
          <TextInput
            style={styles.chatInput}
            placeholder="Type a message..."
            placeholderTextColor={Colors.textMuted}
            value={input}
            onChangeText={setInput}
            returnKeyType="send"
            onSubmitEditing={handleSend}
            multiline
            maxLength={1000}
          />
          <TouchableOpacity
            style={[styles.sendBtn, (!input.trim() || sending) && styles.sendBtnDisabled]}
            onPress={handleSend}
            disabled={!input.trim() || sending}
            activeOpacity={0.7}
          >
            {sending ? (
              <ActivityIndicator size="small" color={Colors.black} />
            ) : (
              <Text style={styles.sendBtnText}>↑</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  centered: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingBottom: 12,
    paddingHorizontal: 16,
    backgroundColor: Colors.bgCard,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  backBtn: { paddingRight: 12, paddingVertical: 4 },
  backBtnText: { fontSize: 22, color: Colors.accent, fontWeight: '700' },
  headerCenter: { flex: 1, flexDirection: 'row', alignItems: 'center' },
  partnerAvatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: Colors.successDim,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    borderWidth: 2,
    borderColor: Colors.success,
  },
  partnerAvatarImg: {
    width: 38,
    height: 38,
    borderRadius: 19,
    marginRight: 10,
    borderWidth: 2,
    borderColor: Colors.success,
    backgroundColor: Colors.bgCard,
  },
  partnerAvatarText: { fontSize: 16, fontWeight: '800', color: Colors.success },
  partnerName: { fontSize: 16, fontWeight: '700', color: Colors.textPrimary },
  partnerStatus: { fontSize: 11, color: Colors.success },
  unmatchBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1.5,
    borderColor: Colors.danger,
  },
  unmatchBtnText: { fontSize: 11, fontWeight: '600', color: Colors.danger },
  messagesList: { paddingHorizontal: 16, paddingVertical: 16, paddingBottom: 8 },
  msgRow: { marginBottom: 8, alignItems: 'flex-start' },
  msgRowMe: { alignItems: 'flex-end' },
  bubble: { maxWidth: '78%', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 20 },
  bubbleMe: { backgroundColor: Colors.accent, borderBottomRightRadius: 4 },
  bubbleThem: { backgroundColor: Colors.bgCard, borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.border },
  bubbleText: { fontSize: 15, lineHeight: 21 },
  bubbleTextMe: { color: Colors.black },
  bubbleTextThem: { color: Colors.textPrimary },
  timeText: { fontSize: 10, marginTop: 4 },
  timeTextMe: { color: 'rgba(0,0,0,0.45)', textAlign: 'right' },
  timeTextThem: { color: Colors.textMuted },
  emptyChat: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyChatEmoji: { fontSize: 48, marginBottom: 12 },
  emptyChatTitle: { fontSize: 20, fontWeight: '700', color: Colors.textPrimary, marginBottom: 6 },
  emptyChatSub: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center' },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingVertical: 10,
    paddingBottom: Platform.OS === 'ios' ? 16 : 10,
    backgroundColor: Colors.bgCard,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    gap: 8,
  },
  chatInput: {
    flex: 1,
    backgroundColor: Colors.bgInput,
    borderRadius: 22,
    paddingHorizontal: 18,
    paddingVertical: 10,
    fontSize: 15,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
    maxHeight: 100,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: { opacity: 0.4 },
  sendBtnText: { fontSize: 20, fontWeight: '800', color: Colors.black, marginTop: -2 },
});
