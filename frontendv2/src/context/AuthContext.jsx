import React, { createContext, useContext, useState, useEffect } from 'react';
import { loadSession, saveSession, clearSession, getUser } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const saved = loadSession();
        if (saved?.id) {
          const fresh = await getUser(saved.id);
          setUser(fresh);
          saveSession(fresh);
        }
      } catch {
        clearSession();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (userId) => {
    const userData = await getUser(userId);
    setUser(userData);
    saveSession(userData);
    return userData;
  };

  const signup = (createdUser) => {
    setUser(createdUser);
    saveSession(createdUser);
  };

  const refreshUser = async () => {
    if (!user?.id) return user;
    try {
      const fresh = await getUser(user.id);
      setUser(fresh);
      saveSession(fresh);
      return fresh;
    } catch {
      return user;
    }
  };

  const logout = () => {
    setUser(null);
    clearSession();
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};
