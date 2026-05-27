import axios from 'axios';

const DEFAULT_BASE = 'http://192.168.1.243:8000/api';

const api = axios.create({
  baseURL: localStorage.getItem('roommatch_api_base') || DEFAULT_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export const setApiBase = (url) => {
  api.defaults.baseURL = url;
  localStorage.setItem('roommatch_api_base', url);
};

// ── User CRUD ──────────────────────────────────────────────────────────────
export const createUser   = (data)          => api.post('/users', data).then(r => r.data);
export const getUser      = (userId)        => api.get(`/users/${userId}`).then(r => r.data);
export const updateUser   = (userId, data)  => api.put(`/users/${userId}`, data).then(r => r.data);
export const deleteUser   = (userId)        => api.delete(`/users/${userId}`).then(r => r.data);

export const uploadPhoto = async (userId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post(`/users/${userId}/upload-photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const getPhotoUrl = (relativePath) => {
  if (!relativePath) return null;
  if (relativePath.startsWith('http')) return relativePath;
  const base = api.defaults.baseURL.replace(/\/api\/?$/, '');
  return `${base}${relativePath}`;
};

// ── Recommendations ────────────────────────────────────────────────────────
export const getTopMatches = (userId) => api.get(`/users/${userId}/top-matches`).then(r => r.data);

// ── Likes & Matching ───────────────────────────────────────────────────────
export const sendLike         = (userId, toUserId) => api.post(`/users/${userId}/like`, { toUser: toUserId }).then(r => r.data);
export const getLikesReceived = (userId)           => api.get(`/users/${userId}/likes-received`).then(r => r.data);
export const getLikesSent     = (userId)           => api.get(`/users/${userId}/likes-sent`).then(r => r.data);
export const getMatches       = (userId)           => api.get(`/users/${userId}/matches`).then(r => r.data);
export const unmatchUser      = (userId, partnerId)=> api.post(`/users/${userId}/unmatch/${partnerId}`).then(r => r.data);

// ── Match Score ────────────────────────────────────────────────────────────
export const getMatchScore = (user1Id, user2Id) =>
  api.post('/matchScore', { user1_id: user1Id, user2_id: user2Id }).then(r => r.data);

// ── Chat ───────────────────────────────────────────────────────────────────
export const getChatConversations = (userId)                  => api.get(`/users/${userId}/chat/conversations`).then(r => r.data);
export const sendChatMessage      = (userId, partnerId, content) => api.post(`/users/${userId}/chat/${partnerId}`, { content }).then(r => r.data);
export const getChatMessages      = (userId, partnerId, limit = 100) => api.get(`/users/${userId}/chat/${partnerId}`, { params: { limit } }).then(r => r.data);

// ── Notifications ──────────────────────────────────────────────────────────
export const getNotifications         = (userId) => api.get(`/users/${userId}/notifications`).then(r => r.data);
export const getUnreadNotificationCount = (userId) => api.get(`/users/${userId}/notifications/unread-count`).then(r => r.data);
export const markNotificationsRead    = (userId) => api.post(`/users/${userId}/notifications/mark-read`).then(r => r.data);

// ── Health ─────────────────────────────────────────────────────────────────
export const healthCheck = () => api.get('/health').then(r => r.data);

// ── Session (localStorage) ─────────────────────────────────────────────────
export const saveSession  = (user) => localStorage.setItem('roommatch_user', JSON.stringify(user));
export const loadSession  = ()     => { const d = localStorage.getItem('roommatch_user'); return d ? JSON.parse(d) : null; };
export const clearSession = ()     => localStorage.removeItem('roommatch_user');

export default api;
