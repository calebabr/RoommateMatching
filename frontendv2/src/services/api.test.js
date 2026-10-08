import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import axios from 'axios';

/**
 * These tests drive the REAL axios instance from `api.js` and stub only the
 * transport, by swapping `api.defaults.adapter`. That keeps the request and
 * response interceptors — the bearer header, the 401 refresh-and-retry, and the
 * refresh queue — in the code path under test, which is the whole point: those
 * interceptors are the part with the interesting behaviour.
 *
 * No test here touches the network, and none depends on a live backend.
 */

// ── Transport stub ─────────────────────────────────────────────────────────

// An axios adapter must return a promise, so both helpers resolve/reject one.
const ok = (data = {}, config) => Promise.resolve({
  data, status: 200, statusText: 'OK', headers: {}, config,
});

const fail = (status, config, data = { detail: 'nope' }) => {
  const err = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.config = config;
  err.response = { status, data, headers: {}, config };
  return Promise.reject(err);
};

/** Fresh module instance per test — api.js keeps refresh state in module scope. */
async function loadApi(handler) {
  vi.resetModules();
  const mod = await import('./api');
  mod.default.defaults.adapter = (config) => {
    calls.push(config);
    return handler(config);
  };
  return mod;
}

let calls = [];
let originalLocation;

beforeEach(() => {
  calls = [];
  localStorage.clear();
  originalLocation = window.location;
  Object.defineProperty(window, 'location', {
    value: { href: '', hostname: 'localhost' },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  Object.defineProperty(window, 'location', {
    value: originalLocation, writable: true, configurable: true,
  });
});

const urlsHit = () => calls.map(c => c.url);

// ── Token / session helpers ────────────────────────────────────────────────

describe('token and session helpers', () => {
  it('round-trips the access token', async () => {
    const api = await loadApi(c => ok({}, c));
    api.saveToken('abc');
    expect(api.loadToken()).toBe('abc');
    api.clearToken();
    expect(api.loadToken()).toBeNull();
  });

  it('stores the refresh token under its own key', async () => {
    const api = await loadApi(c => ok({}, c));
    api.saveToken('access');
    api.saveRefreshToken('refresh');
    expect(localStorage.getItem('token')).toBe('access');
    expect(localStorage.getItem('roommatch_refresh_token')).toBe('refresh');
  });

  it('clearing one token does not clear the other', async () => {
    const api = await loadApi(c => ok({}, c));
    api.saveToken('access');
    api.saveRefreshToken('refresh');
    api.clearToken();
    expect(api.loadRefreshToken()).toBe('refresh');
  });

  it('round-trips the session object', async () => {
    const api = await loadApi(c => ok({}, c));
    api.saveSession({ id: 7, username: 'ada' });
    expect(api.loadSession()).toEqual({ id: 7, username: 'ada' });
    api.clearSession();
    expect(api.loadSession()).toBeNull();
  });
});

// ── Request interceptor ────────────────────────────────────────────────────

describe('request interceptor', () => {
  it('attaches the bearer token when one is stored', async () => {
    const api = await loadApi(c => ok({}, c));
    api.saveToken('tok123');
    await api.healthCheck();
    expect(calls[0].headers.Authorization).toBe('Bearer tok123');
  });

  it('sends no Authorization header when signed out', async () => {
    const api = await loadApi(c => ok({}, c));
    await api.healthCheck();
    expect(calls[0].headers.Authorization).toBeUndefined();
  });
});

// ── Filter serialization (P3FT.16) ─────────────────────────────────────────

describe('getTopMatches — filter serialization', () => {
  it('sends no params at all when no filters are supplied', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [] }, c));
    await api.getTopMatches(1);
    expect(calls[0].params).toBeUndefined();
    expect(calls[0].url).toBe('/users/1/top-matches');
  });

  it('sends no params when the filter object is empty', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [] }, c));
    await api.getTopMatches(1, {});
    expect(calls[0].params).toBeUndefined();
  });

  it('serializes repeatable tags as ?tags=A&tags=B, never comma-joined', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [] }, c));
    await api.getTopMatches(1, { tags: ['Night Owl', 'Fitness'] });

    const { url, params } = calls[0];
    expect(params).toBeInstanceOf(URLSearchParams);
    expect(params.getAll('tags')).toEqual(['Night Owl', 'Fitness']);

    // What axios actually puts on the wire.
    const uri = axios.getUri({ url, params });
    expect(uri).toBe('/users/1/top-matches?tags=Night+Owl&tags=Fitness');
    expect(uri).not.toContain('%2C');
  });

  it('serializes repeatable majors the same way', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [] }, c));
    await api.getTopMatches(1, { major: ['Engineering', 'Nursing'] });
    expect(axios.getUri({ url: calls[0].url, params: calls[0].params }))
      .toBe('/users/1/top-matches?major=Engineering&major=Nursing');
  });

  it('sends mixed repeatable and scalar filters together', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [] }, c));
    await api.getTopMatches(1, {
      tags: ['Gaming'], religion: 'Christian', budgetMax: '900',
    });
    const { params } = calls[0];
    expect(params.getAll('tags')).toEqual(['Gaming']);
    expect(params.get('religion')).toBe('Christian');
    expect(params.get('budgetMax')).toBe('900');
  });

  it('returns the filteredOut count to the caller', async () => {
    const api = await loadApi(c => ok({ userId: 1, matches: [], filteredOut: 4 }, c));
    const data = await api.getTopMatches(1, { tags: ['Gaming'] });
    expect(data.filteredOut).toBe(4);
  });
});

// ── Profile prompts opt-out (P3FT.14) ──────────────────────────────────────

describe('getProfilePrompts', () => {
  it('opts out of the auth-redirect path', async () => {
    const api = await loadApi(c => ok([], c));
    await api.getProfilePrompts();
    expect(calls[0].url).toBe('/profile-prompts');
    expect(calls[0]._skipAuthRedirect).toBe(true);
  });

  it('a 401 here does NOT clear the session or redirect', async () => {
    // Signup fetches this before a token exists. A redirect here would bounce a
    // half-finished signup to /login.
    const api = await loadApi(c => fail(401, c));
    api.saveToken('tok');
    api.saveRefreshToken('refresh');

    await expect(api.getProfilePrompts()).rejects.toBeTruthy();

    expect(api.loadToken()).toBe('tok');
    expect(api.loadRefreshToken()).toBe('refresh');
    expect(window.location.href).toBe('');
    expect(urlsHit()).toEqual(['/profile-prompts']);
  });
});

// ── 401 interceptor ────────────────────────────────────────────────────────

describe('401 interceptor — refresh and retry', () => {
  it('refreshes, then retries the original request with the new token', async () => {
    let failedOnce = false;
    const api = await loadApi((c) => {
      if (c.url === '/auth/refresh') {
        return ok({ access_token: 'new-access', refresh_token: 'new-refresh' }, c);
      }
      if (!failedOnce) { failedOnce = true; return fail(401, c); }
      return ok({ matches: ['ok'] }, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');

    const data = await api.getMatches(1);

    expect(data).toEqual({ matches: ['ok'] });
    expect(urlsHit()).toEqual(['/users/1/matches', '/auth/refresh', '/users/1/matches']);
    expect(calls[2].headers.Authorization).toBe('Bearer new-access');
  });

  it('stores both rotated tokens', async () => {
    let failedOnce = false;
    const api = await loadApi((c) => {
      if (c.url === '/auth/refresh') {
        return ok({ access_token: 'new-access', refresh_token: 'new-refresh' }, c);
      }
      if (!failedOnce) { failedOnce = true; return fail(401, c); }
      return ok({}, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('old-refresh');

    await api.getMatches(1);

    expect(api.loadToken()).toBe('new-access');
    expect(api.loadRefreshToken()).toBe('new-refresh');
  });

  it('signs out when there is no refresh token', async () => {
    const api = await loadApi(c => fail(401, c));
    api.saveToken('stale');
    api.saveSession({ id: 1 });

    await expect(api.getMatches(1)).rejects.toBeTruthy();

    expect(api.loadToken()).toBeNull();
    expect(api.loadSession()).toBeNull();
    expect(window.location.href).toBe('/login');
    expect(urlsHit()).toEqual(['/users/1/matches']);
  });

  it('signs out when the refresh call itself fails', async () => {
    const api = await loadApi(c => fail(401, c));
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');
    api.saveSession({ id: 1 });

    await expect(api.getMatches(1)).rejects.toBeTruthy();

    expect(api.loadToken()).toBeNull();
    expect(api.loadRefreshToken()).toBeNull();
    expect(api.loadSession()).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('does not try to refresh a failing /auth/refresh call — no infinite loop', async () => {
    const api = await loadApi(c => fail(401, c));
    api.saveRefreshToken('refresh-tok');

    await expect(api.authRefresh('refresh-tok')).rejects.toBeTruthy();

    expect(urlsHit()).toEqual(['/auth/refresh']);
    expect(api.loadRefreshToken()).toBeNull();
  });

  it('retries a request only once', async () => {
    const api = await loadApi((c) => {
      if (c.url === '/auth/refresh') {
        return ok({ access_token: 'a', refresh_token: 'b' }, c);
      }
      return fail(401, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');

    await expect(api.getMatches(1)).rejects.toBeTruthy();

    // original, refresh, one retry — and then it stops.
    expect(urlsHit()).toEqual(['/users/1/matches', '/auth/refresh', '/users/1/matches']);
  });

  it('passes non-401 errors straight through without touching the session', async () => {
    const api = await loadApi(c => fail(500, c));
    api.saveToken('tok');
    api.saveRefreshToken('refresh');

    await expect(api.getMatches(1)).rejects.toMatchObject({ response: { status: 500 } });

    expect(api.loadToken()).toBe('tok');
    expect(window.location.href).toBe('');
    expect(urlsHit()).toEqual(['/users/1/matches']);
  });

  it('does not intercept a 403', async () => {
    const api = await loadApi(c => fail(403, c));
    api.saveToken('tok');
    api.saveRefreshToken('refresh');
    await expect(api.getMatches(1)).rejects.toBeTruthy();
    expect(api.loadToken()).toBe('tok');
  });
});

describe('401 interceptor — the refresh queue', () => {
  it('refreshes once for concurrent 401s and retries both', async () => {
    const failed = new Set();
    let refreshCount = 0;
    let releaseRefresh;
    const refreshGate = new Promise((resolve) => { releaseRefresh = resolve; });

    const api = await loadApi(async (c) => {
      if (c.url === '/auth/refresh') {
        refreshCount += 1;
        await refreshGate;               // hold the refresh open so both 401s land
        return ok({ access_token: 'new-access', refresh_token: 'new-refresh' }, c);
      }
      if (!failed.has(c.url)) { failed.add(c.url); return fail(401, c); }
      return ok({ url: c.url }, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');

    const first = api.getMatches(1);
    const second = api.getLikesSent(1);
    // Let both original requests fail before the refresh resolves.
    await new Promise(r => setTimeout(r, 0));
    releaseRefresh();

    const [a, b] = await Promise.all([first, second]);

    expect(refreshCount).toBe(1);
    expect(a).toEqual({ url: '/users/1/matches' });
    expect(b).toEqual({ url: '/users/1/likes-sent' });
  });

  it('retries the queued request with the refreshed token', async () => {
    const failed = new Set();
    let releaseRefresh;
    const refreshGate = new Promise((resolve) => { releaseRefresh = resolve; });

    const api = await loadApi(async (c) => {
      if (c.url === '/auth/refresh') {
        await refreshGate;
        return ok({ access_token: 'new-access', refresh_token: 'new-refresh' }, c);
      }
      if (!failed.has(c.url)) { failed.add(c.url); return fail(401, c); }
      return ok({}, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');

    const first = api.getMatches(1);
    const second = api.getLikesSent(1);
    await new Promise(r => setTimeout(r, 0));
    releaseRefresh();
    await Promise.all([first, second]);

    const retried = calls.filter(c => c.url === '/users/1/likes-sent');
    expect(retried).toHaveLength(2);
    expect(retried[1].headers.Authorization).toBe('Bearer new-access');
  });

  it('rejects every queued request when the refresh fails', async () => {
    const failed = new Set();
    let releaseRefresh;
    const refreshGate = new Promise((resolve) => { releaseRefresh = resolve; });

    const api = await loadApi(async (c) => {
      if (c.url === '/auth/refresh') {
        await refreshGate;
        return fail(401, c);
      }
      if (!failed.has(c.url)) { failed.add(c.url); return fail(401, c); }
      return ok({}, c);
    });
    api.saveToken('stale');
    api.saveRefreshToken('refresh-tok');

    const first = api.getMatches(1).catch(e => e);
    const second = api.getLikesSent(1).catch(e => e);
    await new Promise(r => setTimeout(r, 0));
    releaseRefresh();

    const [a, b] = await Promise.all([first, second]);
    expect(a).toBeInstanceOf(Error);
    expect(b).toBeInstanceOf(Error);
    expect(api.loadToken()).toBeNull();
  });
});

// ── A few request shapes worth pinning ─────────────────────────────────────

describe('request shapes', () => {
  it('sendLike posts the target in the body', async () => {
    const api = await loadApi(c => ok({ status: 'liked' }, c));
    await api.sendLike(1, 2);
    expect(calls[0].url).toBe('/users/1/like');
    expect(calls[0].method).toBe('post');
    expect(JSON.parse(calls[0].data)).toEqual({ toUser: 2 });
  });

  it('cancelLike issues a DELETE against the pair', async () => {
    const api = await loadApi(c => ok({}, c));
    await api.cancelLike(1, 2);
    expect(calls[0].method).toBe('delete');
    expect(calls[0].url).toBe('/users/1/like/2');
  });

  it('getChatMessages passes the limit', async () => {
    const api = await loadApi(c => ok({ messages: [] }, c));
    await api.getChatMessages(1, 2, 25);
    expect(calls[0].url).toBe('/users/1/chat/2');
    expect(calls[0].params).toEqual({ limit: 25 });
  });

  it('authLogout swallows failures so sign-out always completes locally', async () => {
    const api = await loadApi(c => fail(500, c));
    await expect(api.authLogout()).resolves.toBeUndefined();
  });
});

describe('getPhotoUrl', () => {
  it('passes an absolute URL straight through', async () => {
    const api = await loadApi(c => ok({}, c));
    expect(api.getPhotoUrl('https://res.cloudinary.com/x.jpg'))
      .toBe('https://res.cloudinary.com/x.jpg');
  });

  it('prefixes a legacy relative path with the API origin', async () => {
    const api = await loadApi(c => ok({}, c));
    expect(api.getPhotoUrl('/uploads/7.jpg')).toBe('http://localhost:8000/uploads/7.jpg');
  });

  it('returns null for a missing path', async () => {
    const api = await loadApi(c => ok({}, c));
    expect(api.getPhotoUrl(null)).toBeNull();
    expect(api.getPhotoUrl('')).toBeNull();
  });
});
