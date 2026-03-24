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
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getChatMessages, sendChatMessage, getUser, getPhotoUrl } from '../services/api';

export default function ChatScreen({ navigation }) {
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [partner, setPartner] = useState(null);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const flatListRef = useRef(null);
    const pollRef = useRef(null);

    const loadMessages = async () => {
        if (!user?.id || !user?.matched) return;
        try {
        const msgs = await getChatMessages(user.id);
        setMessages(msgs);
        } catch {}
    };

    const loadPartner = async () => {
        if (!user?.matchedWith) return;
        try {
        const p = await getUser(user.matchedWith);
        setPartner(p);
        } catch {
        setPartner({ id: user.matchedWith, username: `User #${user.matchedWith}` });
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
        }, [user?.id, user?.matchedWith])
    );

    const handleSend = async () => {
        const text = input.trim();
        if (!text) return;
        setSending(true);
        setInput('');
        try {
        await sendChatMessage(user.id, text);
        await loadMessages();
        setTimeout(() => { flatListRef.current?.scrollToEnd({ animated: true }); }, 100);
        } catch (err) {
        const msg = err?.response?.data?.detail || 'Could not send message.';
        Alert.alert('Error', msg);
        setInput(text);
        } finally {
        setSending(false);
        }
    };

    const getTimeStr = (dateStr) => {
        const d = new Date(dateStr);
        const h = d.getHours();
        const m = d.getMinutes().toString().padStart(2, '0');
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
        return `${h12}:${m} ${ampm}`;
    };

    if (!user?.matched) {
        return (
        <View style={styles.centered}>
            <Text style={styles.emoji}>💬</Text>
            <Text style={styles.emptyTitle}>No Chat Available</Text>
            <Text style={styles.emptySubtitle}>Chat becomes available after you match with a roommate.</Text>
        </View>
        );
    }

    if (loading) {
        return (
        <View style={styles.centered}>
            <ActivityIndicator size="large" color={Colors.accent} />
            <Text style={styles.loadingText}>Loading chat...</Text>
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
        <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
        <View style={styles.header}>
            <View style={styles.headerContent}>
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
                <Text style={styles.partnerStatus}>Your matched roommate</Text>
            </View>
            </View>
        </View>

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
    );
    }

    const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: Colors.bg },
    centered: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center', padding: 40 },
    emoji: { fontSize: 56, marginBottom: 16 },
    emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
    emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
    loadingText: { fontSize: 14, color: Colors.textSecondary, marginTop: 16 },
    header: { paddingTop: Platform.OS === 'ios' ? 60 : 40, paddingBottom: 14, paddingHorizontal: 20, backgroundColor: Colors.bgCard, borderBottomWidth: 1, borderBottomColor: Colors.border },
    headerContent: { flexDirection: 'row', alignItems: 'center' },
    partnerAvatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.successDim, alignItems: 'center', justifyContent: 'center', marginRight: 12, borderWidth: 2, borderColor: Colors.success },
    partnerAvatarImg: { width: 40, height: 40, borderRadius: 20, marginRight: 12, borderWidth: 2, borderColor: Colors.success, backgroundColor: Colors.bgCard },
    partnerAvatarText: { fontSize: 18, fontWeight: '800', color: Colors.success },
    partnerName: { fontSize: 17, fontWeight: '700', color: Colors.textPrimary },
    partnerStatus: { fontSize: 12, color: Colors.success, marginTop: 1 },
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
    inputBar: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 12, paddingVertical: 10, paddingBottom: Platform.OS === 'ios' ? 34 : 10, backgroundColor: Colors.bgCard, borderTopWidth: 1, borderTopColor: Colors.border, gap: 8 },
    chatInput: { flex: 1, backgroundColor: Colors.bgInput, borderRadius: 22, paddingHorizontal: 18, paddingVertical: 10, fontSize: 15, color: Colors.textPrimary, borderWidth: 1, borderColor: Colors.border, maxHeight: 100 },
    sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.accent, alignItems: 'center', justifyContent: 'center' },
    sendBtnDisabled: { opacity: 0.4 },
    sendBtnText: { fontSize: 20, fontWeight: '800', color: Colors.black, marginTop: -2 },
});