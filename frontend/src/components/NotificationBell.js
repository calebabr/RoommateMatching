import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getUnreadNotificationCount } from '../services/api';

export default function NotificationBell({ onPress }) {
    const { user } = useAuth();
    const [count, setCount] = useState(0);
    const intervalRef = useRef(null);

    const fetchCount = async () => {
        if (!user?.id) return;
        try {
        const data = await getUnreadNotificationCount(user.id);
        setCount(data.count || 0);
        } catch {
        // silent fail
        }
    };

    useEffect(() => {
        fetchCount();
        // Poll every 5 seconds for new notifications
        intervalRef.current = setInterval(fetchCount, 5000);
        return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [user?.id]);

    return (
        <TouchableOpacity style={styles.bellBtn} onPress={onPress} activeOpacity={0.7}>
        <Text style={styles.bellIcon}>🔔</Text>
        {count > 0 && (
            <View style={styles.badge}>
            <Text style={styles.badgeText}>{count > 99 ? '99+' : count}</Text>
            </View>
        )}
        </TouchableOpacity>
    );
    }

    const styles = StyleSheet.create({
    bellBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: Colors.bgCard,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
        borderColor: Colors.border,
        position: 'relative',
    },
    bellIcon: { fontSize: 18 },
    badge: {
        position: 'absolute',
        top: -4,
        right: -4,
        backgroundColor: Colors.danger,
        borderRadius: 10,
        minWidth: 20,
        height: 20,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 5,
        borderWidth: 2,
        borderColor: Colors.bg,
    },
    badgeText: { fontSize: 10, fontWeight: '800', color: Colors.white },
});