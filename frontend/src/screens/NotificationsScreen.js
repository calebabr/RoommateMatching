import React, { useState, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    FlatList,
    TouchableOpacity,
    ActivityIndicator,
    RefreshControl,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getNotifications, markNotificationsRead, getUser } from '../services/api';

export default function NotificationsScreen({ navigation }) {
    const { user } = useAuth();
    const insets = useSafeAreaInsets();
    const [notifications, setNotifications] = useState([]);
    const [profiles, setProfiles] = useState({});
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const loadNotifications = async () => {
        if (!user?.id) return;
        try {
        const data = await getNotifications(user.id);
        setNotifications(data);

        // Mark all as read
        await markNotificationsRead(user.id);

        // Fetch unique user profiles for avatars
        const uniqueIds = [...new Set(data.map((n) => n.fromUser))];
        const profileMap = { ...profiles };
        await Promise.all(
            uniqueIds
            .filter((id) => !profileMap[id])
            .map(async (id) => {
                try {
                const p = await getUser(id);
                profileMap[id] = p;
                } catch {
                profileMap[id] = { id, username: `User #${id}` };
                }
            })
        );
        setProfiles(profileMap);
        } catch {
        setNotifications([]);
        }
    };

    useFocusEffect(
        useCallback(() => {
        let active = true;
        (async () => {
            setLoading(true);
            await loadNotifications();
            if (active) setLoading(false);
        })();
        return () => { active = false; };
        }, [user?.id])
    );

    const handleRefresh = async () => {
        setRefreshing(true);
        await loadNotifications();
        setRefreshing(false);
    };

    const getNotifIcon = (type) => {
        switch (type) {
        case 'like_received': return '💌';
        case 'match_created': return '🎉';
        case 'unmatch': return '💔';
        default: return '🔔';
        }
    };

    const getNotifColor = (type) => {
        switch (type) {
        case 'like_received': return Colors.danger;
        case 'match_created': return Colors.success;
        case 'unmatch': return Colors.textMuted;
        default: return Colors.accent;
        }
    };

    const getTimeAgo = (dateStr) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return `${diffH}h ago`;
        const diffD = Math.floor(diffH / 24);
        if (diffD < 7) return `${diffD}d ago`;
        return date.toLocaleDateString();
    };

    if (loading) {
        return (
        <View style={styles.centered}>
            <ActivityIndicator size="large" color={Colors.accent} />
        </View>
        );
    }

    const renderNotification = ({ item }) => {
        const p = profiles[item.fromUser];
        const icon = getNotifIcon(item.type);
        const color = getNotifColor(item.type);

        return (
        <TouchableOpacity
            style={[styles.card, !item.read && styles.cardUnread]}
            onPress={() => {
            if (item.type === 'like_received' || item.type === 'match_created') {
                navigation.navigate('UserDetail', { userId: item.fromUser });
            }
            }}
            activeOpacity={0.8}
        >
            <View style={[styles.iconCircle, { backgroundColor: color + '20', borderColor: color }]}>
            <Text style={styles.iconEmoji}>{icon}</Text>
            </View>
            <View style={styles.cardContent}>
            <Text style={styles.notifMessage}>{item.message}</Text>
            <Text style={styles.notifTime}>{getTimeAgo(item.createdAt)}</Text>
            </View>
            {!item.read && <View style={[styles.unreadDot, { backgroundColor: color }]} />}
        </TouchableOpacity>
        );
    };

    return (
        <View style={styles.container}>
        <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
            <TouchableOpacity onPress={() => navigation.goBack()}>
            <Text style={styles.backBtn}>← Back</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Activity</Text>
            <View style={{ width: 60 }} />
        </View>

        {notifications.length === 0 ? (
            <View style={styles.centered}>
            <Text style={styles.emoji}>🔔</Text>
            <Text style={styles.emptyTitle}>No Activity Yet</Text>
            <Text style={styles.emptySubtitle}>
                Likes, matches, and updates will appear here.
            </Text>
            </View>
        ) : (
            <FlatList
            data={notifications}
            keyExtractor={(item) => item.id}
            renderItem={renderNotification}
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
            refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={Colors.accent} />
            }
            />
        )}
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
        paddingBottom: 12,
        borderBottomWidth: 1,
        borderBottomColor: Colors.border,
    },
    backBtn: { fontSize: 16, color: Colors.accent, fontWeight: '600', width: 60 },
    headerTitle: { fontSize: 20, fontWeight: '800', color: Colors.textPrimary },
    list: { paddingHorizontal: 16, paddingBottom: 30 },
    card: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: Colors.bgCard,
        borderRadius: Radius.md,
        padding: 16,
        marginTop: 10,
        borderWidth: 1,
        borderColor: Colors.border,
    },
    cardUnread: {
        borderColor: Colors.accent + '40',
        backgroundColor: Colors.accentGlow,
    },
    iconCircle: {
        width: 44,
        height: 44,
        borderRadius: 22,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1.5,
        marginRight: 14,
    },
    iconEmoji: { fontSize: 20 },
    cardContent: { flex: 1 },
    notifMessage: { fontSize: 14, fontWeight: '600', color: Colors.textPrimary, lineHeight: 20 },
    notifTime: { fontSize: 12, color: Colors.textMuted, marginTop: 4 },
    unreadDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginLeft: 8,
    },
    centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
    emoji: { fontSize: 56, marginBottom: 16 },
    emptyTitle: { fontSize: 22, fontWeight: '700', color: Colors.textPrimary, marginBottom: 8 },
    emptySubtitle: { fontSize: 14, color: Colors.textSecondary, textAlign: 'center', lineHeight: 20 },
});