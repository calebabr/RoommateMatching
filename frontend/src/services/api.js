import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Change this to your backend URL
const API_BASE = 'http://172.17.202.174:8000/api';

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

export const uploadPhoto = async (userId, imageUri) => {
  const formData = new FormData();
  // Get filename and type from URI
  const uriParts = imageUri.split('/');
  const fileName = uriParts[uriParts.length - 1];
  const ext = fileName.split('.').pop()?.toLowerCase() || 'jpg';
  const mimeType = ext === 'png' ? 'image/png' : ext === 'gif' ? 'image/gif' : 'image/jpeg';

  formData.append('file', {
    uri: imageUri,
    name: fileName,
    type: mimeType,
  });

  const res = await api.post(`/users/${userId}/upload-photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// Helper to build full photo URL from a relative path
export const getPhotoUrl = (relativePath) => {
  if (!relativePath) return null;
  if (relativePath.startsWith('http')) return relativePath;
  // Strip /api from baseURL to get server root
  const base = api.defaults.baseURL.replace(/\/api\/?$/, '');
  return `${base}${relativePath}`;
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

export const unmatchUser = async (userId, partnerId) => {
  const res = await api.post(`/users/${userId}/unmatch/${partnerId}`);
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

// ─── Chat ────────────────────────────────────────────────

export const getChatConversations = async (userId) => {
  const res = await api.get(`/users/${userId}/chat/conversations`);
  return res.data;
};

export const sendChatMessage = async (userId, partnerId, content) => {
  const res = await api.post(`/users/${userId}/chat/${partnerId}`, { content });
  return res.data;
};

export const getChatMessages = async (userId, partnerId, limit = 100) => {
  const res = await api.get(`/users/${userId}/chat/${partnerId}`, { params: { limit } });
  return res.data;
};

// ─── Notifications ───────────────────────────────────────

export const getNotifications = async (userId) => {
  const res = await api.get(`/users/${userId}/notifications`);
  return res.data;
};

export const getUnreadNotificationCount = async (userId) => {
  const res = await api.get(`/users/${userId}/notifications/unread-count`);
  return res.data;
};

export const markNotificationsRead = async (userId) => {
  const res = await api.post(`/users/${userId}/notifications/mark-read`);
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