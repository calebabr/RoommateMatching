import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

/**
 * The like / match flow on the Discover page (P3T.5).
 *
 * Everything below the flow under test is stubbed: the API module, the auth
 * context, and the three chrome components that fetch on their own
 * (NotificationBell, RoommateFoundBanner, DiscoverFilterBar). Modal and
 * PromptCards are left real, because the match celebration and the prompt cards
 * are part of what the flow is supposed to render.
 *
 * No network, no backend.
 */

vi.mock('../services/api', () => ({
  getTopMatches: vi.fn(),
  getLikesSent: vi.fn(),
  getUser: vi.fn(),
  sendLike: vi.fn(),
  skipUser: vi.fn(),
  getPhotoUrl: vi.fn(() => null),
  // PromptCards is left unmocked, and it fetches the prompt catalogue.
  getProfilePrompts: vi.fn(() => Promise.resolve([])),
}));

const refreshUser = vi.fn();
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, username: 'me', lifestyleTags: ['Gaming'] },
    refreshUser,
  }),
}));

vi.mock('../components/NotificationBell', () => ({ default: () => null }));
vi.mock('../components/RoommateFoundBanner', () => ({ default: () => null }));
vi.mock('../components/DiscoverFilterBar', () => ({ default: () => null }));

import {
  getLikesSent, getTopMatches, getUser, sendLike, skipUser,
} from '../services/api';
import DiscoverPage from './DiscoverPage';

const CANDIDATES = {
  2: { id: 2, username: 'bea', gender: 'female', bio: 'Likes plants', lifestyleTags: ['Gaming'] },
  3: { id: 3, username: 'cyd', gender: 'female', bio: 'Night owl', lifestyleTags: [] },
};

/** Seed the page with candidates and (optionally) already-sent likes. */
function seed({ matches = [[2, 0.9], [3, 0.7]], likesSent = [], filteredOut } = {}) {
  const payload = { userId: 1, matches: matches.map(([id, s]) => ({ user_id: id, compatibilityScore: s })) };
  if (filteredOut !== undefined) payload.filteredOut = filteredOut;
  getTopMatches.mockResolvedValue(payload);
  getLikesSent.mockResolvedValue(likesSent);
  getUser.mockImplementation(id => Promise.resolve(CANDIDATES[id]));
}

// The future flags only silence react-router's v7 deprecation warnings so a
// failing assertion is not buried in console noise.
const renderPage = () =>
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DiscoverPage />
    </MemoryRouter>,
  );

/** The card element for a candidate, located by their username. */
const cardFor = (username) =>
  screen.getByText(username).closest('.discover-card');

const likeButtonFor = (username) =>
  within(cardFor(username)).getByRole('button', { name: /Like/ });

const passButtonFor = (username) =>
  within(cardFor(username)).getByRole('button', { name: /Pass/ });

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe('loading the feed', () => {
  it('shows a spinner state before the feed arrives', async () => {
    seed();
    renderPage();
    expect(screen.getByText(/Finding compatible roommates/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());
  });

  it('renders one card per recommended candidate', async () => {
    seed();
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());
    expect(screen.getByText('cyd')).toBeInTheDocument();
    expect(screen.getByText('2 compatible roommates')).toBeInTheDocument();
  });

  it('renders the compatibility percentage from the stored score', async () => {
    seed();
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());
    expect(within(cardFor('bea')).getByText('90%')).toBeInTheDocument();
    expect(within(cardFor('cyd')).getByText('70%')).toBeInTheDocument();
  });

  it('requests the feed for the signed-in user', async () => {
    seed();
    renderPage();
    await waitFor(() => expect(getTopMatches).toHaveBeenCalled());
    expect(getTopMatches).toHaveBeenCalledWith(1, expect.any(Object));
  });

  it('shows the empty state when nothing is recommended', async () => {
    seed({ matches: [] });
    renderPage();
    await waitFor(() => expect(screen.getByText('No Matches Yet')).toBeInTheDocument());
  });

  it('shows an error state when the feed request fails', async () => {
    getTopMatches.mockRejectedValue(new Error('500'));
    getLikesSent.mockResolvedValue([]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("Couldn't Load Matches")).toBeInTheDocument());
  });

  it('treats a fully filtered-out result as empty, not as an error', async () => {
    // 200 {matches: [], filteredOut: N} is a normal empty result.
    seed({ matches: [], filteredOut: 4 });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText('No Matches Yet')).toBeInTheDocument());
    expect(screen.queryByText("Couldn't Load Matches")).not.toBeInTheDocument();
  });
});

describe('liking someone', () => {
  it('sends the like for the clicked candidate', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'liked' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    expect(sendLike).toHaveBeenCalledWith(1, 2);
    expect(sendLike).toHaveBeenCalledTimes(1);
  });

  it('flips that card to Pending when the like is one-sided', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'liked' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() =>
      expect(within(cardFor('bea')).getByText('✓ Pending')).toBeInTheDocument());
    expect(within(cardFor('bea')).queryByRole('button', { name: /Like/ }))
      .not.toBeInTheDocument();
  });

  it('leaves the other cards untouched', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'liked' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() =>
      expect(within(cardFor('bea')).getByText('✓ Pending')).toBeInTheDocument());
    expect(likeButtonFor('cyd')).toBeInTheDocument();
  });

  it('does not celebrate a one-sided like', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'liked' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() =>
      expect(within(cardFor('bea')).getByText('✓ Pending')).toBeInTheDocument());
    expect(screen.queryByText(/It's a Match/)).not.toBeInTheDocument();
  });

  it('renders Pending for likes already sent before the page loaded', async () => {
    seed({ likesSent: [2] });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    expect(within(cardFor('bea')).getByText('✓ Pending')).toBeInTheDocument();
    expect(likeButtonFor('cyd')).toBeInTheDocument();
  });
});

describe('a mutual like becomes a match', () => {
  it('celebrates the match', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'matched' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() =>
      expect(screen.getByText("🎉 It's a Match!")).toBeInTheDocument());
    expect(screen.getByText(/are now roommate matches/)).toBeInTheDocument();
  });

  it('refreshes the signed-in user so the new match count lands', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'matched' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() => expect(refreshUser).toHaveBeenCalled());
  });

  it('reloads the feed so the matched user drops out of Discover', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'matched' });
    renderPage();
    await waitFor(() => expect(getTopMatches).toHaveBeenCalledTimes(1));

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() => expect(getTopMatches).toHaveBeenCalledTimes(2));
  });

  it('dismisses the celebration on OK', async () => {
    seed();
    sendLike.mockResolvedValue({ status: 'matched' });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));
    await waitFor(() =>
      expect(screen.getByText("🎉 It's a Match!")).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'OK' }));

    await waitFor(() =>
      expect(screen.queryByText("🎉 It's a Match!")).not.toBeInTheDocument());
  });
});

describe('a like that fails', () => {
  it('surfaces the server message', async () => {
    seed();
    sendLike.mockRejectedValue({
      response: { data: { detail: 'You have reached the maximum of 5 matches' } },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument());
    expect(screen.getByText('You have reached the maximum of 5 matches'))
      .toBeInTheDocument();
  });

  it('falls back to a generic message when the server sends none', async () => {
    seed();
    sendLike.mockRejectedValue(new Error('network'));
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() =>
      expect(screen.getByText('Could not send like.')).toBeInTheDocument());
  });

  it('does not mark the card as Pending', async () => {
    seed();
    sendLike.mockRejectedValue(new Error('network'));
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument());
    expect(within(cardFor('bea')).queryByText('✓ Pending')).not.toBeInTheDocument();
  });

  it('re-enables the like button so the user can retry', async () => {
    seed();
    sendLike.mockRejectedValue(new Error('network'));
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(likeButtonFor('bea'));

    await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument());
    expect(likeButtonFor('bea')).toBeEnabled();
  });
});

describe('passing on someone', () => {
  it('skips the clicked candidate', async () => {
    seed();
    skipUser.mockResolvedValue({});
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(passButtonFor('bea'));

    expect(skipUser).toHaveBeenCalledWith(1, 2);
  });

  it('removes the card from the feed', async () => {
    seed();
    skipUser.mockResolvedValue({});
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(passButtonFor('bea'));

    await waitFor(() => expect(screen.queryByText('bea')).not.toBeInTheDocument());
    expect(screen.getByText('cyd')).toBeInTheDocument();
  });

  it('keeps the card and explains when the skip fails', async () => {
    seed();
    skipUser.mockRejectedValue({ response: { data: { detail: 'Already skipped' } } });
    renderPage();
    await waitFor(() => expect(screen.getByText('bea')).toBeInTheDocument());

    await userEvent.click(passButtonFor('bea'));

    await waitFor(() => expect(screen.getByText('Already skipped')).toBeInTheDocument());
    expect(screen.getByText('bea')).toBeInTheDocument();
  });
});
