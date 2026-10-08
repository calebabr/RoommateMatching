import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

// The api module is mocked, but the token/session helpers are backed by real
// localStorage so the rehydrate-on-mount path behaves the way it does in the
// browser rather than against a bag of unrelated spies.
vi.mock('../services/api', () => ({
  authLogin: vi.fn(),
  authRegister: vi.fn(),
  authMe: vi.fn(),
  authLogout: vi.fn(),
  saveToken: vi.fn(t => localStorage.setItem('token', t)),
  loadToken: vi.fn(() => localStorage.getItem('token')),
  clearToken: vi.fn(() => localStorage.removeItem('token')),
  saveRefreshToken: vi.fn(t => localStorage.setItem('roommatch_refresh_token', t)),
  clearRefreshToken: vi.fn(() => localStorage.removeItem('roommatch_refresh_token')),
  saveSession: vi.fn(u => localStorage.setItem('roommatch_user', JSON.stringify(u))),
  clearSession: vi.fn(() => localStorage.removeItem('roommatch_user')),
}));

import posthog from 'posthog-js';
import * as api from '../services/api';
import { AuthProvider, useAuth } from './AuthContext';

const USER = { id: 7, username: 'ada', email: 'ada@auburn.edu' };

const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

/** Render the hook and wait for the mount-time rehydrate to settle. */
async function renderAuth() {
  const utils = renderHook(() => useAuth(), { wrapper });
  await waitFor(() => expect(utils.result.current.loading).toBe(false));
  return utils;
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe('mount-time rehydrate', () => {
  it('starts signed out when there is no stored token', async () => {
    const { result } = await renderAuth();
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(api.authMe).not.toHaveBeenCalled();
  });

  it('restores the user from a stored token', async () => {
    localStorage.setItem('token', 'stored-token');
    api.authMe.mockResolvedValue(USER);

    const { result } = await renderAuth();

    expect(api.authMe).toHaveBeenCalledTimes(1);
    expect(result.current.user).toEqual(USER);
    expect(result.current.token).toBe('stored-token');
  });

  it('caches the rehydrated user in the session', async () => {
    localStorage.setItem('token', 'stored-token');
    api.authMe.mockResolvedValue(USER);
    await renderAuth();
    expect(api.saveSession).toHaveBeenCalledWith(USER);
  });

  it('clears a stale token when /me rejects', async () => {
    localStorage.setItem('token', 'expired');
    api.authMe.mockRejectedValue(new Error('401'));

    const { result } = await renderAuth();

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(api.clearToken).toHaveBeenCalled();
    expect(api.clearSession).toHaveBeenCalled();
  });

  it('always finishes loading, even when /me rejects', async () => {
    localStorage.setItem('token', 'expired');
    api.authMe.mockRejectedValue(new Error('401'));
    const { result } = await renderAuth();
    expect(result.current.loading).toBe(false);
  });
});

describe('login', () => {
  it('stores both tokens and the user', async () => {
    api.authLogin.mockResolvedValue({
      access_token: 'access', refresh_token: 'refresh', user: USER,
    });
    const { result } = await renderAuth();

    await act(async () => { await result.current.login('ada@auburn.edu', 'pw'); });

    expect(api.authLogin).toHaveBeenCalledWith('ada@auburn.edu', 'pw');
    expect(api.saveToken).toHaveBeenCalledWith('access');
    expect(api.saveRefreshToken).toHaveBeenCalledWith('refresh');
    expect(api.saveSession).toHaveBeenCalledWith(USER);
    expect(result.current.user).toEqual(USER);
    expect(result.current.token).toBe('access');
  });

  it('returns the user to the caller', async () => {
    api.authLogin.mockResolvedValue({ access_token: 'a', user: USER });
    const { result } = await renderAuth();

    let returned;
    await act(async () => { returned = await result.current.login('e', 'p'); });
    expect(returned).toEqual(USER);
  });

  it('tolerates a response with no refresh token', async () => {
    api.authLogin.mockResolvedValue({ access_token: 'access', user: USER });
    const { result } = await renderAuth();

    await act(async () => { await result.current.login('e', 'p'); });

    expect(api.saveRefreshToken).not.toHaveBeenCalled();
    expect(result.current.user).toEqual(USER);
  });

  it('identifies the user to analytics', async () => {
    api.authLogin.mockResolvedValue({ access_token: 'a', user: USER });
    const { result } = await renderAuth();
    await act(async () => { await result.current.login('e', 'p'); });

    expect(posthog.identify).toHaveBeenCalledWith('7');
    expect(posthog.capture).toHaveBeenCalledWith('login', { method: 'email' });
  });

  it('propagates a failed login and leaves the user signed out', async () => {
    api.authLogin.mockRejectedValue(new Error('bad credentials'));
    const { result } = await renderAuth();

    await expect(
      act(async () => { await result.current.login('e', 'wrong'); }),
    ).rejects.toThrow('bad credentials');

    expect(result.current.user).toBeNull();
    expect(api.saveToken).not.toHaveBeenCalled();
  });
});

describe('signup', () => {
  it('stores tokens and the user the same way login does', async () => {
    api.authRegister.mockResolvedValue({
      access_token: 'access', refresh_token: 'refresh', user: USER,
    });
    const { result } = await renderAuth();

    await act(async () => {
      await result.current.signup('ada@auburn.edu', 'pw', { username: 'ada' });
    });

    expect(api.authRegister).toHaveBeenCalledWith(
      'ada@auburn.edu', 'pw', { username: 'ada' },
    );
    expect(result.current.user).toEqual(USER);
    expect(result.current.token).toBe('access');
    expect(posthog.capture).toHaveBeenCalledWith('signup_completed');
  });

  it('propagates a failed signup', async () => {
    api.authRegister.mockRejectedValue(new Error('email taken'));
    const { result } = await renderAuth();

    await expect(
      act(async () => { await result.current.signup('e', 'p', {}); }),
    ).rejects.toThrow('email taken');
    expect(result.current.user).toBeNull();
  });
});

describe('logout', () => {
  async function signedIn() {
    api.authLogin.mockResolvedValue({
      access_token: 'access', refresh_token: 'refresh', user: USER,
    });
    const utils = await renderAuth();
    await act(async () => { await utils.result.current.login('e', 'p'); });
    return utils;
  }

  it('clears the user, both tokens and the session', async () => {
    api.authLogout.mockResolvedValue({});
    const { result } = await signedIn();

    await act(async () => { await result.current.logout(); });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(api.clearToken).toHaveBeenCalled();
    expect(api.clearRefreshToken).toHaveBeenCalled();
    expect(api.clearSession).toHaveBeenCalled();
  });

  it('tells the server to revoke the refresh token', async () => {
    api.authLogout.mockResolvedValue({});
    const { result } = await signedIn();
    await act(async () => { await result.current.logout(); });
    expect(api.authLogout).toHaveBeenCalled();
  });

  it('signs out locally even when the server call fails', async () => {
    // A failed revoke must never strand the user in a half-signed-in state.
    api.authLogout.mockRejectedValue(new Error('offline'));
    const { result } = await signedIn();

    await act(async () => { await result.current.logout(); });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(api.clearToken).toHaveBeenCalled();
  });

  it('resets the analytics identity', async () => {
    api.authLogout.mockResolvedValue({});
    const { result } = await signedIn();
    await act(async () => { await result.current.logout(); });
    expect(posthog.capture).toHaveBeenCalledWith('logout');
    expect(posthog.reset).toHaveBeenCalled();
  });
});

describe('refreshUser', () => {
  async function signedIn() {
    localStorage.setItem('token', 'access');
    api.authMe.mockResolvedValue(USER);
    return renderAuth();
  }

  it('replaces the user with the freshly fetched one', async () => {
    const { result } = await signedIn();
    const updated = { ...USER, username: 'ada2' };
    api.authMe.mockResolvedValue(updated);

    let returned;
    await act(async () => { returned = await result.current.refreshUser(); });

    expect(result.current.user).toEqual(updated);
    expect(returned).toEqual(updated);
  });

  it('updates the cached session too', async () => {
    const { result } = await signedIn();
    const updated = { ...USER, username: 'ada2' };
    api.authMe.mockResolvedValue(updated);
    await act(async () => { await result.current.refreshUser(); });
    expect(api.saveSession).toHaveBeenLastCalledWith(updated);
  });

  it('keeps the existing user when the fetch fails', async () => {
    const { result } = await signedIn();
    api.authMe.mockRejectedValue(new Error('offline'));

    let returned;
    await act(async () => { returned = await result.current.refreshUser(); });

    expect(result.current.user).toEqual(USER);
    expect(returned).toEqual(USER);
  });

  it('never rejects, so a caller awaiting it cannot break the page', async () => {
    const { result } = await signedIn();
    api.authMe.mockRejectedValue(new Error('offline'));
    await expect(
      act(async () => { await result.current.refreshUser(); }),
    ).resolves.not.toThrow();
  });

  it('does not call the API when signed out', async () => {
    const { result } = await renderAuth();
    api.authMe.mockClear();

    await act(async () => { await result.current.refreshUser(); });

    expect(api.authMe).not.toHaveBeenCalled();
  });
});

describe('useAuth guard', () => {
  it('throws when used outside the provider', () => {
    // React logs the thrown error; silence it so the run stays readable.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow(
      'useAuth must be inside AuthProvider',
    );
    spy.mockRestore();
  });
});
