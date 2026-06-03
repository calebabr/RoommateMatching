import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const adminLogin = (email, password) =>
  api.post('/api/auth/login', { email, password });

export const adminGetMe = () => api.get('/api/auth/me');

export const adminGetUsers = () => api.get('/api/admin/users');

export const adminGetUser = (id) => api.get(`/api/users/${id}`);

export const adminBanUser = (id) => api.post(`/api/admin/ban/${id}`);

export const adminUnbanUser = (id) => api.post(`/api/admin/unban/${id}`);

export const adminGetUserActivity = (id) => api.get(`/api/admin/users/${id}/activity`);
