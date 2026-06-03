import { createContext, useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminLogin } from '../services/adminApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [adminUser, setAdminUser] = useState(() => {
    try {
      const stored = localStorage.getItem('admin_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [adminToken, setAdminToken] = useState(() =>
    localStorage.getItem('admin_token') || null
  );

  const navigate = useNavigate();

  async function login(email, password) {
    const res = await adminLogin(email, password);
    const { access_token, user } = res.data;
    if (!user.is_admin) {
      throw new Error('Not an admin account.');
    }
    localStorage.setItem('admin_token', access_token);
    localStorage.setItem('admin_user', JSON.stringify(user));
    setAdminToken(access_token);
    setAdminUser(user);
    navigate('/users');
  }

  function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    setAdminToken(null);
    setAdminUser(null);
    navigate('/login');
  }

  return (
    <AuthContext.Provider value={{ adminUser, adminToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAdmin() {
  return useContext(AuthContext);
}
