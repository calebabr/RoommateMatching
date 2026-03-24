import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    FlatList,
    TextInput,
    TouchableOpacity,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Image,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getMessages, sendMessage, getUser, getPhotoUrl } from '../services/api';

const POLL_INTERVAL = 3000; // 3 seconds

export default function ChatScreen({ route, navigation }) {
    const { partnerId, partnerName: initialName } = route.params;
    const insets = useSafeAreaInsets();
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [text, setText] = useState('');
    const [sending, setSending] = useState(false);
    const [loading, setLoading] = useState(true);
    const [partner, setPartner] = useState({ username: initialName || `User #${partnerId}`, photoUrl: '' });
    const flatListRef = useRef(null);
    const lastTimestampRef = useRef(null);
    const pollRef = useRef(null);

    // Load partner profile
    useEffect(() => {
        (async () => {
        try {
            const p = await getUser(partnerId);
            setPartner(p);
            navigation.setOptions({ title: p.username });
        } catch {}
        })();
    }, [partnerId]);

    // Fetch messages
    const fetchMessages = useCallback(async (isInitial = false) => {
        if (!user?.id) return;
        try {
        const after = isInitial ? null : lastTimestampRef.current;
        const data = await getMessages(user.id, partnerId, after);
        const newMsgs = data.messages || [];

        if (newMsgs.length > 0) {
            lastTimestampRef.current = newMsgs[newMsgs.length - 1].sentAt;

            if (isInitial) {
            setMessages(newMsgs);
            } else {
            setMessages((prev) => {
                // Deduplicate by _id
                const existingIds = new Set(prev.map((m) => m._id));
                const unique = newMsgs.filter((m) => !existingIds.has(m._id));
                if (unique.length === 0) return prev;
                return [...prev, ...unique];
            });
            }
        }
        } catch (err) {
        console.warn('Failed to fetch messages:', err);
        } finally {
        if (isInitial) setLoading(false);
        }
    }, [user?.id, partnerId]);

    // Initial load
    useEffect(() => {
        fetchMessages(true);
    }, [fetchMessages]);

    // Polling
    useEffect(() => {
        pollRef.current = setInterval(() => fetchMessages(false), POLL_INTERVAL);
        return () => {
        if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [fetchMessages]);

    // Auto-scroll when new messages arrive
    useEffect(() => {
        if (messages.length > 0 && flatListRef.current) {
        setTimeout(() => {
            flatListRef.current?.scrollToEnd({ animated: true });
        }, 100);
        }
    }, [messages.length]);

    const handleSend = async () => {
        const trimmed = text.trim();
        if (!trimmed || sending) return;

        setSending(true);
        setText('');

        try {
        const msg = await sendMessage(user.id, partnerId, trimmed);
        // Add optimistically
        const formatted = {
            ...msg,
            sentAt: msg.sentAt || new Date().toISOString(),
        };
        setMessages((prev) => [...prev, formatted]);
        lastTimestampRef.current = formatted.sentAt;
        } catch (err) {
        console.warn('Failed to send:', err);
        setText(trimmed); // Restore text on failure
        } finally {
        setSending(false);
        }
    };

    const resolvedPhoto = getPhotoUrl(partner.photoUrl);

    const renderMessage = ({ item }) => {
        const isMe = item.senderId === user?.id;
        return (
        <View style={[styles.messageBubbleWrap, isMe ? styles.myWrap : styles.theirWrap]}>
            <View style={[styles.bubble, isMe ? styles.myBubble : styles.theirBubble]}>
            <Text style={[styles.bubbleText, isMe ? styles.myBubbleText : styles.theirBubbleText]}>
                {item.text}
            </Text>
            <Text style={[styles.bubbleTime, isMe ? styles.myBubbleTime : styles.theirBubbleTime]}>
                {formatTime(item.sentAt)}
            </Text>
            </View>
        </View>
        );
    };

    return (
        <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={0}
        >
        {/* Header */}
        <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
            <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
            <Text style={styles.backText}>←</Text>
            </TouchableOpacity>
            <View style={styles.headerProfile}>
            {resolvedPhoto ? (
                <Image source={{ uri: resolvedPhoto }} style={styles.headerAvatar} />
            ) : (
                <View style={styles.headerAvatarFallback}>
                <Text style={styles.headerAvatarText}>
                    {(partner.username || '?')[0].toUpperCase()}
                </Text>
                </View>
            )}
            <Text style={styles.headerName} numberOfLines={1}>{partner.username}</Text>
            </View>
            <View style={styles.backButton} />
        </View>

        {/* Messages */}
        {loading ? (
            <View style={styles.centered}>
            <ActivityIndicator size="large" color={Colors.accent} />
            </View>
        ) : messages.length === 0 ? (
            <View style={styles.centered}>
            <Text style={styles.emptyEmoji}>👋</Text>
            <Text style={styles.emptyTitle}>Say hello!</Text>
            <Text style={styles.emptySubtitle}>
                Start a conversation with {partner.username}.
            </Text>
            </View>
        ) : (
            <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item._id || `${item.sentAt}-${item.senderId}`}
            renderItem={renderMessage}
            contentContainerStyle={styles.messageList}
            showsVerticalScrollIndicator={false}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
            />
        )}

        {/* Input */}
        <View style={[styles.inputBar, { paddingBottom: insets.bottom + 8 }]}>
            <TextInput
            style={styles.textInput}
            placeholder="Type a message..."
            placeholderTextColor={Colors.textMuted}
            value={text}
            onChangeText={setText}
            multiline
            maxLength={2000}
            returnKeyType="default"
            />
            <TouchableOpacity
            style={[styles.sendBtn, (!text.trim() || sending) && styles.sendBtnDisabled]}
            onPress={handleSend}
            disabled={!text.trim() || sending}
            activeOpacity={0.7}
            >
            {sending ? (
                <ActivityIndicator size="small" color={Colors.black} />
            ) : (
                <Text style={styles.sendBtnText}>Send</Text>
            )}
            </TouchableOpacity>
        </View>
        </KeyboardAvoidingView>
    );
}

function formatTime(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        const now = new Date();
        const isToday = d.toDateString() === now.toDateString();
        if (isToday) {
        return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        }
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
        ' ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    } catch {
        return '';
    }
    }

    const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: Colors.bg },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingBottom: 12,
        backgroundColor: Colors.bgCard,
        borderBottomWidth: 1,
        borderBottomColor: Colors.border,
    },
    backButton: { width: 44, alignItems: 'center' },
    backText: { fontSize: 24, color: Colors.accent, fontWeight: '600' },
    headerProfile: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
    headerAvatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: Colors.bgCard },
    headerAvatarFallback: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: Colors.accentGlow,
        alignItems: 'center',
        justifyContent: 'center',
    },
    headerAvatarText: { fontSize: 16, fontWeight: '700', color: Colors.accent },
    headerName: { fontSize: 17, fontWeight: '700', color: Colors.textPrimary, maxWidth: 180 },
    centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
    emptyEmoji: { fontSize: 48, marginBottom: 12 },
    emptyTitle: { fontSize: 20, fontWeight: '700', color: Colors.textPrimary, marginBottom: 6 },
    emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center' },
    messageList: { paddingHorizontal: 16, paddingVertical: 12 },
    messageBubbleWrap: { marginBottom: 8 },
    myWrap: { alignItems: 'flex-end' },
    theirWrap: { alignItems: 'flex-start' },
    bubble: {
        maxWidth: '78%',
        borderRadius: 18,
        paddingHorizontal: 14,
        paddingVertical: 10,
    },
    myBubble: {
        backgroundColor: Colors.accent,
        borderBottomRightRadius: 4,
    },
    theirBubble: {
        backgroundColor: Colors.bgCard,
        borderBottomLeftRadius: 4,
        borderWidth: 1,
        borderColor: Colors.border,
    },
    bubbleText: { fontSize: 15, lineHeight: 21 },
    myBubbleText: { color: Colors.black },
    theirBubbleText: { color: Colors.textPrimary },
    bubbleTime: { fontSize: 10, marginTop: 4 },
    myBubbleTime: { color: 'rgba(0,0,0,0.45)', textAlign: 'right' },
    theirBubbleTime: { color: Colors.textMuted },
    inputBar: {
        flexDirection: 'row',
        alignItems: 'flex-end',
        paddingHorizontal: 12,
        paddingTop: 10,
        backgroundColor: Colors.bgCard,
        borderTopWidth: 1,
        borderTopColor: Colors.border,
        gap: 8,
    },
    textInput: {
        flex: 1,
        backgroundColor: Colors.bgInput,
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 10,
        fontSize: 15,
        color: Colors.textPrimary,
        maxHeight: 100,
        borderWidth: 1,
        borderColor: Colors.border,
    },
    sendBtn: {
        backgroundColor: Colors.accent,
        borderRadius: 20,
        paddingHorizontal: 18,
        paddingVertical: 10,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 2,
    },
    sendBtnDisabled: { opacity: 0.4 },
    sendBtnText: { fontSize: 15, fontWeight: '700', color: Colors.black },
});