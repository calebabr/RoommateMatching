import axios from 'axios';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SESSION_KEY = 'roommatch_session';

// Default: use your machine's local IP for Expo Go on a real device
// Change this to your server's IP address
let API_URL = 'http://172.20.10.2:8000';

export function setApiBase(url) {
  API_URL = url.replace(/\/+$/, '');
}

export function getApiBase() {
  return API_URL;
}

const api = () =>
  axios.create({
    baseURL: API_URL,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
  });

// --- Helper: resolve photo URLs ---
// photoUrl from the DB may be a relative server path like "/uploads/photos/123_abc.jpg"
// or an empty string / null. This returns a full URL or null.
export function getPhotoUrl(photoUrl) {
  if (!photoUrl || photoUrl.trim() === '') return null;
  // Already a full URL (http/https)
  if (photoUrl.startsWith('http://') || photoUrl.startsWith('https://')) {
    return photoUrl;
  }
  // Relative path from our server
  return `${API_URL}${photoUrl}`;
}

// --- Users ---

export async function createUser(data) {
  const res = await api().post('/api/users', data);
  return res.data;
}

export async function getUser(userId) {
  const res = await api().get(`/api/users/${userId}`);
  return res.data;
}

export async function updateUser(userId, data) {
  const res = await api().put(`/api/users/${userId}`, data);
  return res.data;
}

export async function deleteUser(userId) {
  const res = await api().delete(`/api/users/${userId}`);
  return res.data;
}

// --- Photo Upload ---

export async function uploadPhoto(userId, imageUri) {
  const formData = new FormData();

  // Get file extension from URI
  const uriParts = imageUri.split('.');
  const ext = uriParts[uriParts.length - 1] || 'jpg';

  // Determine mime type
  const mimeMap = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', heic: 'image/heic' };
  const mimeType = mimeMap[ext.toLowerCase()] || 'image/jpeg';

  formData.append('file', {
    uri: Platform.OS === 'ios' ? imageUri.replace('file://', '') : imageUri,
    name: `photo_${userId}.${ext}`,
    type: mimeType,
  });

  const res = await axios.post(`${API_URL}/api/users/${userId}/photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  });
  return res.data;
}

export async function deletePhoto(userId) {
  const res = await api().delete(`/api/users/${userId}/photo`);
  return res.data;
}

// --- Recommendations ---

export async function getTopMatches(userId) {
  const res = await api().get(`/api/users/${userId}/top-matches`);
  return res.data;
}

export async function getMatchScore(userId1, userId2) {
  const res = await api().post('/api/matchScore', {
    user1_id: userId1,
    user2_id: userId2,
  });
  return res.data;
}

// --- Likes & Matching ---

export async function sendLike(fromUserId, toUserId) {
  const res = await api().post(`/api/users/${fromUserId}/like`, {
    toUser: toUserId,
  });
  return res.data;
}

export async function getLikesReceived(userId) {
  const res = await api().get(`/api/users/${userId}/likes-received`);
  return res.data;
}

export async function getMatches(userId) {
  const res = await api().get(`/api/users/${userId}/matches`);
  return res.data;
}

export async function unmatchUser(userId) {
  const res = await api().post(`/api/users/${userId}/unmatch`);
  return res.data;
}

// --- Admin ---

export async function recomputeAll() {
  const res = await api().post('/api/admin/recompute');
  return res.data;
}

// --- Session Persistence ---

export async function saveSession(userData) {
  try {
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(userData));
  } catch (e) {
    console.warn('Failed to save session:', e);
  }
}

export async function loadSession() {
  try {
    const raw = await AsyncStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('Failed to load session:', e);
    return null;
  }
}

export async function clearSession() {
  try {
    await AsyncStorage.removeItem(SESSION_KEY);
  } catch (e) {
    console.warn('Failed to clear session:', e);
  }
}

// --- Chat ---

export async function sendMessage(userId, receiverId, text) {
  const res = await api().post(`/api/chat/${userId}/send`, {
    receiverId,
    text,
  });
  return res.data;
}

export async function getMessages(userId, otherUserId, after = null, limit = 50) {
  const params = { limit };
  if (after) params.after = after;
  const res = await api().get(`/api/chat/${userId}/messages/${otherUserId}`, { params });
  return res.data;
}

export async function getConversations(userId) {
  const res = await api().get(`/api/chat/${userId}/conversations`);
  return res.data;
}