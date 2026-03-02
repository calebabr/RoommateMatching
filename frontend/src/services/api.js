// ──────────────────────────────────────────────────────
// API Service — connects to the FastAPI backend
// ──────────────────────────────────────────────────────
//
// IMPORTANT: Update API_BASE when running on a physical device.
// "localhost" only works in iOS Simulator or Android Emulator
// with `adb reverse tcp:8000 tcp:8000`.
//
// For a real phone on Wi-Fi, use your computer's LAN IP:
//   const API_BASE = 'http://192.168.1.XX:8000/api';

const API_BASE = 'http://172.17.201.88:8000/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }
    return data;
  } catch (err) {
    if (err.message === 'Network request failed') {
      throw new Error(
        'Cannot reach the backend. Make sure the server is running at ' + API_BASE
      );
    }
    throw err;
  }
}

// ── User CRUD ──

export function createUser(userData) {
  return request('/users', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
}

export function getUser(userId) {
  return request(`/users/${userId}`);
}

export function updateProfile(userId, userData) {
  return request(`/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(userData),
  });
}

export function deleteUser(userId) {
  return request(`/users/${userId}`, { method: 'DELETE' });
}

export function getAllUsers() {
  return request('/users/all');
}

// ── Recommendations ──

export function getTopMatches(userId) {
  return request(`/users/${userId}/top-matches`);
}

// ── Likes & Matching ──

export function likeUser(fromUserId, toUserId) {
  return request(`/users/${fromUserId}/like`, {
    method: 'POST',
    body: JSON.stringify({ toUser: toUserId }),
  });
}

export function getLikesReceived(userId) {
  return request(`/users/${userId}/likes-received`);
}

export function getMatches(userId) {
  return request(`/users/${userId}/matches`);
}

export function unmatchUser(userId) {
  return request(`/users/${userId}/unmatch`, { method: 'POST' });
}

// ── Compatibility ──

export function getMatchScore(user1Id, user2Id) {
  return request('/matchScore', {
    method: 'POST',
    body: JSON.stringify({ user1_id: user1Id, user2_id: user2Id }),
  });
}
