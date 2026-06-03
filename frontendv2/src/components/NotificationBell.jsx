import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
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
      className="notif-bell-btn"
      onClick={() => navigate('/notifications')}
    >
      <span className="notif-bell-icon">🔔</span>
      {count > 0 && (
        <span className="notif-bell-badge">
          {count > 99 ? '99+' : count}
        </span>
      )}
    </button>
  );
}
