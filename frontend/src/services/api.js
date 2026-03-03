import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Change this to your backend URL
const API_BASE = 'http://172.20.10.2:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── User CRUD ───────────────────────────────────────────

export const createUser = async (userData) => {
  const res = await api.post('/users', userData);
  return res.data;
};

export const getUser = async (userId) => {
  const res = await api.get(`/users/${userId}`);
  return res.data;
};

export const updateUser = async (userId, userData) => {
  const res = await api.put(`/users/${userId}`, userData);
  return res.data;
};

export const deleteUser = async (userId) => {
  const res = await api.delete(`/users/${userId}`);
  return res.data;
};

// ─── Recommendations ─────────────────────────────────────

export const getTopMatches = async (userId) => {
  const res = await api.get(`/users/${userId}/top-matches`);
  return res.data;
};

// ─── Likes & Matching ────────────────────────────────────

export const sendLike = async (userId, toUserId) => {
  const res = await api.post(`/users/${userId}/like`, { toUser: toUserId });
  return res.data;
};

export const getLikesReceived = async (userId) => {
  const res = await api.get(`/users/${userId}/likes-received`);
  return res.data;
};

export const getMatches = async (userId) => {
  const res = await api.get(`/users/${userId}/matches`);
  return res.data;
};

export const unmatchUser = async (userId) => {
  const res = await api.post(`/users/${userId}/unmatch`);
  return res.data;
};

// ─── Match Score ─────────────────────────────────────────

export const getMatchScore = async (user1Id, user2Id) => {
  const res = await api.post('/matchScore', {
    user1_id: user1Id,
    user2_id: user2Id,
  });
  return res.data;
};

// ─── Health Check ────────────────────────────────────────

export const healthCheck = async () => {
  const res = await api.get('/health');
  return res.data;
};

// ─── Local Auth Storage ──────────────────────────────────

export const saveSession = async (user) => {
  await AsyncStorage.setItem('roommatch_user', JSON.stringify(user));
};

export const loadSession = async () => {
  const data = await AsyncStorage.getItem('roommatch_user');
  return data ? JSON.parse(data) : null;
};

export const clearSession = async () => {
  await AsyncStorage.removeItem('roommatch_user');
};

export const setApiBase = (url) => {
  api.defaults.baseURL = url;
};

export default api;
