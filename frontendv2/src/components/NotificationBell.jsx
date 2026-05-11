import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { useAuth } from '../context/AuthContext';
import { getUnreadNotificationCount } from '../services/api';

export default function NotificationBell() {
  const navigate = useNavigate();
  const { user }  = useAuth();
  const [count, setCount] = useState(0);
  const timerRef = useRef(null);

  const fetchCount = async () => {
    if (!user?.id) return;
    try {
      const data = await getUnreadNotificationCount(user.id);
      setCount(data.count || 0);
    } catch {}
  };

  useEffect(() => {
    fetchCount();
    timerRef.current = setInterval(fetchCount, 5000);
    return () => clearInterval(timerRef.current);
  }, [user?.id]);

  return (
    <button
      onClick={() => navigate('/notifications')}
      style={{
        width: 40, height: 40,
        borderRadius: '50%',
        backgroundColor: Colors.bgCard,
        border: `1px solid ${Colors.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        position: 'relative',
        cursor: 'pointer',
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 18 }}>🔔</span>
      {count > 0 && (
        <span style={{
          position: 'absolute', top: -4, right: -4,
          backgroundColor: Colors.danger,
          borderRadius: Radius.full,
          minWidth: 18, height: 18,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          paddingLeft: 4, paddingRight: 4,
          fontSize: 10, fontWeight: 800, color: Colors.white,
          border: `2px solid ${Colors.bg}`,
        }}>
          {count > 99 ? '99+' : count}
        </span>
      )}
    </button>
  );
}
