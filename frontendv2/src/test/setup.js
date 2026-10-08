import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// PostHog is imported at module scope by AuthContext and several pages. Every
// call is fire-and-forget analytics, and a real client would try to open a
// network connection from the test run, so it is stubbed suite-wide.
vi.mock('posthog-js', () => ({
  default: {
    init: vi.fn(),
    identify: vi.fn(),
    capture: vi.fn(),
    reset: vi.fn(),
  },
}));

afterEach(() => {
  cleanup();
  localStorage.clear();
});
