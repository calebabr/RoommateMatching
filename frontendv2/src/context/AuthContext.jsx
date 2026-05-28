import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  authLogin, authRegister, authMe,
  saveToken, loadToken, clearToken,
  saveSession, clearSession,
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);
  const [token,   setToken]   = useState(() => loadToken());
  const [loading, setLoading] = useState(true);

  // Rehydrate user state on app load using stored JWT
  useEffect(() => {
    (async () => {
      const stored = loadToken();
      if (stored) {
        try {
          const me = await authMe();
          setUser(me);
          saveSession(me);
        } catch {
          clearToken();
          clearSession();
          setToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email, password) => {
    const { access_token, user: userData } = await authLogin(email, password);
    saveToken(access_token);
    setToken(access_token);
    setUser(userData);
    saveSession(userData);
    return userData;
  };

  const signup = async (email, password, profileData) => {
    const { access_token, user: userData } = await authRegister(email, password, profileData);
    saveToken(access_token);
    setToken(access_token);
    setUser(userData);
    saveSession(userData);
    return userData;
  };

  const refreshUser = async () => {
    if (!token) return user;
    try {
      const fresh = await authMe();
      setUser(fresh);
      saveSession(fresh);
      return fresh;
    } catch {
      return user;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    clearToken();
    clearSession();
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout, refreshUser, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};
