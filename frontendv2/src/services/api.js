import axios from 'axios';

const DEFAULT_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api'
  : 'https://roommatematching.onrender.com/api';

const api = axios.create({
  baseURL: DEFAULT_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

export const setApiBase = (url) => {
  api.defaults.baseURL = url;
  localStorage.setItem('roommatch_api_base', url);
};

// ── Token helpers ──────────────────────────────────────────────────────────
export const saveToken  = (token) => localStorage.setItem('token', token);
export const loadToken  = ()      => localStorage.getItem('token');
export const clearToken = ()      => localStorage.removeItem('token');

export const saveRefreshToken  = (t) => localStorage.setItem('roommatch_refresh_token', t);
export const loadRefreshToken  = ()  => localStorage.getItem('roommatch_refresh_token');
export const clearRefreshToken = ()  => localStorage.removeItem('roommatch_refresh_token');

// Attach JWT on every request
api.interceptors.request.use((config) => {
  const token = loadToken();
  if (token) config.headers['Authorization'] = `Bearer ${token}`;
  return config;
});

// ── Auth ───────────────────────────────────────────────────────────────────
export const authLogin         = (email, password)            => api.post('/auth/login', { email, password }).then(r => r.data);
export const authRegister      = (email, password, data)      => api.post('/auth/register', { email, password, ...data }).then(r => r.data);
export const authMe            = ()                            => api.get('/auth/me').then(r => r.data);
export const authForgotPassword = (email)                     => api.post('/auth/forgot-password', { email }).then(r => r.data);
export const authResetPassword  = (token, newPassword)        => api.post('/auth/reset-password', { token, new_password: newPassword }).then(r => r.data);
export const authRefresh       = (refreshToken)               => api.post('/auth/refresh', { refresh_token: refreshToken }).then(r => r.data);
export const authLogout        = ()                           => api.post('/auth/logout').then(r => r.data).catch(() => {});

// ── 401 interceptor with token refresh ────────────────────────────────────
let _isRefreshing = false;
let _refreshQueue = [];

const _processQueue = (error, token = null) => {
  _refreshQueue.forEach(({ resolve, reject }) => error ? reject(error) : resolve(token));
  _refreshQueue = [];
};

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err?.response?.status === 401 && !original._retry) {
      const refreshToken = loadRefreshToken();
      // Don't try to refresh if the failing call was itself the refresh endpoint
      if (!refreshToken || original.url?.includes('/auth/refresh')) {
        clearToken(); clearRefreshToken(); clearSession();
        window.location.href = '/login';
        return Promise.reject(err);
      }
      if (_isRefreshing) {
        // Queue this request to retry once refresh completes
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then(token => {
          original.headers['Authorization'] = `Bearer ${token}`;
          return api(original);
        });
      }
      original._retry = true;
      _isRefreshing = true;
      try {
        const data = await api.post('/auth/refresh', { refresh_token: refreshToken }).then(r => r.data);
        saveToken(data.access_token);
        saveRefreshToken(data.refresh_token);
        api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        _processQueue(null, data.access_token);
        original.headers['Authorization'] = `Bearer ${data.access_token}`;
        return api(original);
      } catch (refreshErr) {
        _processQueue(refreshErr, null);
        clearToken(); clearRefreshToken(); clearSession();
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      } finally {
        _isRefreshing = false;
      }
    }
    return Promise.reject(err);
  }
);

// ── User CRUD ──────────────────────────────────────────────────────────────
export const createUser   = (data)          => api.post('/users', data).then(r => r.data);
export const getUser      = (userId)        => api.get(`/users/${userId}`).then(r => r.data);
export const updateUser   = (userId, data)  => api.put(`/users/${userId}`, data).then(r => r.data);
export const deleteUser   = (userId)        => api.delete(`/users/${userId}`).then(r => r.data);

// ── Block system ───────────────────────────────────────────────────────────
export const blockUser       = (userId)                        => api.post(`/users/${userId}/block`).then(r => r.data);
export const unblockUser     = (userId)                        => api.post(`/users/${userId}/unblock`).then(r => r.data);
export const getBlockedUsers = (userId)                        => api.get(`/users/${userId}/blocked`).then(r => r.data);

// ── Report system ──────────────────────────────────────────────────────────
export const reportUser = (userId, reportedId, reason, description) =>
  api.post(`/users/${userId}/report/${reportedId}`, { reason, description }).then(r => r.data);

// ── Account deletion / restore / export ───────────────────────────────────
export const deleteAccount  = (userId, password) => api.delete(`/users/${userId}`, { data: { password } }).then(r => r.data);
export const restoreAccount = (token)            => api.post('/auth/restore-account', { token }).then(r => r.data);
export const exportUserData = (userId)           => api.get(`/users/${userId}/export`).then(r => r.data);

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

// ── Age verification ───────────────────────────────────────────────────────
export const submitAge = (userId, dateOfBirth) =>
  api.post(`/users/${userId}/submit-age`, { dateOfBirth }).then(r => r.data);

// ── Terms of Service ───────────────────────────────────────────────────────
export const acceptTerms = (userId, termsVersion) =>
  api.post(`/users/${userId}/accept-terms`, { termsVersion }).then(r => r.data);

// ── Feedback ───────────────────────────────────────────────────────────────
export const submitFeedback = (message) => api.post('/feedback', { message });

// ── Health ─────────────────────────────────────────────────────────────────
export const healthCheck = () => api.get('/health').then(r => r.data);

// ── Session (localStorage) ─────────────────────────────────────────────────
export const saveSession  = (user) => localStorage.setItem('roommatch_user', JSON.stringify(user));
export const loadSession  = ()     => { const d = localStorage.getItem('roommatch_user'); return d ? JSON.parse(d) : null; };
export const clearSession = ()     => localStorage.removeItem('roommatch_user');

export default api;
