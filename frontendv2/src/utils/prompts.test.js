import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

vi.mock('../services/api', () => ({ getProfilePrompts: vi.fn() }));

import { getProfilePrompts } from '../services/api';
import {
  MAX_PROMPT_ANSWERS,
  PROMPT_ANSWER_MAX_LENGTH,
  availablePrompts,
  displayablePromptAnswers,
  loadProfilePrompts,
  promptTextFor,
  resetProfilePromptsCache,
  sanitizePromptAnswers,
  useProfilePrompts,
} from './prompts';

const CATALOGUE = [
  { id: 'ideal_saturday', text: 'My ideal Saturday looks like…' },
  { id: 'my_study_style', text: 'My study style is…' },
];

beforeEach(() => {
  resetProfilePromptsCache();
  vi.mocked(getProfilePrompts).mockReset();
});

describe('loadProfilePrompts — failure handling', () => {
  it('resolves to [] instead of rejecting when the fetch fails', async () => {
    getProfilePrompts.mockRejectedValue(new Error('network down'));
    await expect(loadProfilePrompts()).resolves.toEqual([]);
  });

  it('resolves to [] on a 500, not just a network error', async () => {
    getProfilePrompts.mockRejectedValue({ response: { status: 500 } });
    await expect(loadProfilePrompts()).resolves.toEqual([]);
  });

  it('does NOT cache a failure, so a later mount retries', async () => {
    getProfilePrompts.mockRejectedValueOnce(new Error('down'));
    expect(await loadProfilePrompts()).toEqual([]);

    getProfilePrompts.mockResolvedValueOnce(CATALOGUE);
    expect(await loadProfilePrompts()).toEqual(CATALOGUE);
    expect(getProfilePrompts).toHaveBeenCalledTimes(2);
  });

  it('does not cache an empty successful response either', async () => {
    getProfilePrompts.mockResolvedValueOnce([]);
    expect(await loadProfilePrompts()).toEqual([]);

    getProfilePrompts.mockResolvedValueOnce(CATALOGUE);
    expect(await loadProfilePrompts()).toEqual(CATALOGUE);
  });
});

describe('loadProfilePrompts — caching and de-duplication', () => {
  it('caches a successful fetch', async () => {
    getProfilePrompts.mockResolvedValue(CATALOGUE);
    await loadProfilePrompts();
    await loadProfilePrompts();
    expect(getProfilePrompts).toHaveBeenCalledTimes(1);
  });

  it('de-dupes concurrent callers into one request', async () => {
    getProfilePrompts.mockResolvedValue(CATALOGUE);
    const [a, b, c] = await Promise.all([
      loadProfilePrompts(), loadProfilePrompts(), loadProfilePrompts(),
    ]);
    expect(getProfilePrompts).toHaveBeenCalledTimes(1);
    expect(a).toEqual(b);
    expect(b).toEqual(c);
  });

  it('resetProfilePromptsCache forces a refetch', async () => {
    getProfilePrompts.mockResolvedValue(CATALOGUE);
    await loadProfilePrompts();
    resetProfilePromptsCache();
    await loadProfilePrompts();
    expect(getProfilePrompts).toHaveBeenCalledTimes(2);
  });
});

describe('loadProfilePrompts — payload normalization', () => {
  it('accepts the documented [{id, text}] array', async () => {
    getProfilePrompts.mockResolvedValue(CATALOGUE);
    expect(await loadProfilePrompts()).toEqual(CATALOGUE);
  });

  it('tolerates a {prompts: [...]} envelope', async () => {
    getProfilePrompts.mockResolvedValue({ prompts: CATALOGUE });
    expect(await loadProfilePrompts()).toEqual(CATALOGUE);
  });

  it('drops entries missing an id or text rather than rendering blanks', async () => {
    getProfilePrompts.mockResolvedValue([
      { id: 'ok', text: 'Fine' },
      { id: '', text: 'No id' },
      { id: 'no_text', text: '' },
      { id: 'null_text', text: null },
      null,
    ]);
    expect(await loadProfilePrompts()).toEqual([{ id: 'ok', text: 'Fine' }]);
  });

  it('resolves to [] for a completely unexpected payload', async () => {
    getProfilePrompts.mockResolvedValue('nope');
    expect(await loadProfilePrompts()).toEqual([]);
  });
});

describe('useProfilePrompts', () => {
  it('flips ready to true after a successful fetch', async () => {
    getProfilePrompts.mockResolvedValue(CATALOGUE);
    const { result } = renderHook(() => useProfilePrompts());
    expect(result.current.ready).toBe(false);
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.prompts).toEqual(CATALOGUE);
  });

  it('flips ready to true after a FAILED fetch, with an empty list', async () => {
    // "Still loading" and "no prompts" must be distinguishable, otherwise the
    // profile pages spin forever during a prompts outage.
    getProfilePrompts.mockRejectedValue(new Error('down'));
    const { result } = renderHook(() => useProfilePrompts());
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.prompts).toEqual([]);
  });

  it('never throws when the fetch fails', async () => {
    getProfilePrompts.mockRejectedValue(new Error('down'));
    const { result } = renderHook(() => useProfilePrompts());
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current).toBeTruthy();
  });
});

describe('degrading to rendering nothing', () => {
  it('promptTextFor returns "" for an unknown id', () => {
    expect(promptTextFor(CATALOGUE, 'retired_prompt')).toBe('');
  });

  it('promptTextFor tolerates a null catalogue', () => {
    expect(promptTextFor(null, 'ideal_saturday')).toBe('');
  });

  it('displayablePromptAnswers drops answers whose prompt copy is unknown', () => {
    const answers = [
      { promptId: 'ideal_saturday', answer: 'Hiking' },
      { promptId: 'retired_prompt', answer: 'Orphaned' },
    ];
    expect(displayablePromptAnswers(answers, CATALOGUE)).toEqual([
      { promptId: 'ideal_saturday', answer: 'Hiking', text: CATALOGUE[0].text },
    ]);
  });

  it('displayablePromptAnswers renders nothing when the catalogue failed to load', () => {
    const answers = [{ promptId: 'ideal_saturday', answer: 'Hiking' }];
    expect(displayablePromptAnswers(answers, [])).toEqual([]);
  });

  it('displayablePromptAnswers tolerates null answers and null prompts', () => {
    expect(displayablePromptAnswers(null, null)).toEqual([]);
    expect(displayablePromptAnswers(undefined, CATALOGUE)).toEqual([]);
  });

  it('displayablePromptAnswers drops an empty answer', () => {
    const answers = [{ promptId: 'ideal_saturday', answer: '' }];
    expect(displayablePromptAnswers(answers, CATALOGUE)).toEqual([]);
  });
});

describe('availablePrompts', () => {
  it('hides prompts the user has already answered', () => {
    const answers = [{ promptId: 'ideal_saturday', answer: 'x' }];
    expect(availablePrompts(CATALOGUE, answers).map(p => p.id)).toEqual(['my_study_style']);
  });

  it('keeps the prompt the open editor row is using', () => {
    const answers = [{ promptId: 'ideal_saturday', answer: 'x' }];
    expect(availablePrompts(CATALOGUE, answers, 'ideal_saturday').map(p => p.id))
      .toEqual(['ideal_saturday', 'my_study_style']);
  });

  it('returns [] when the catalogue is unavailable', () => {
    expect(availablePrompts(null, [])).toEqual([]);
  });
});

describe('sanitizePromptAnswers — matches the API contract', () => {
  it('trims whitespace', () => {
    expect(sanitizePromptAnswers([{ promptId: 'a', answer: '  hi  ' }]))
      .toEqual([{ promptId: 'a', answer: 'hi' }]);
  });

  it('drops blank and whitespace-only answers', () => {
    expect(sanitizePromptAnswers([
      { promptId: 'a', answer: '' },
      { promptId: 'b', answer: '   ' },
    ])).toEqual([]);
  });

  it('drops entries with no promptId', () => {
    expect(sanitizePromptAnswers([{ promptId: '', answer: 'hi' }])).toEqual([]);
  });

  it(`caps an answer at ${PROMPT_ANSWER_MAX_LENGTH} characters`, () => {
    const [out] = sanitizePromptAnswers([{ promptId: 'a', answer: 'x'.repeat(400) }]);
    expect(out.answer).toHaveLength(PROMPT_ANSWER_MAX_LENGTH);
  });

  it(`keeps at most ${MAX_PROMPT_ANSWERS} answers`, () => {
    const answers = ['a', 'b', 'c', 'd', 'e'].map(id => ({ promptId: id, answer: 'x' }));
    expect(sanitizePromptAnswers(answers)).toHaveLength(MAX_PROMPT_ANSWERS);
  });

  it('drops duplicate promptIds, keeping the first', () => {
    const out = sanitizePromptAnswers([
      { promptId: 'a', answer: 'first' },
      { promptId: 'a', answer: 'second' },
    ]);
    expect(out).toEqual([{ promptId: 'a', answer: 'first' }]);
  });

  it('drops ids that are not in the supplied catalogue', () => {
    const out = sanitizePromptAnswers(
      [{ promptId: 'ideal_saturday', answer: 'ok' }, { promptId: 'ghost', answer: 'no' }],
      CATALOGUE,
    );
    expect(out).toEqual([{ promptId: 'ideal_saturday', answer: 'ok' }]);
  });

  it('accepts any id when no catalogue is supplied', () => {
    expect(sanitizePromptAnswers([{ promptId: 'anything', answer: 'ok' }]))
      .toEqual([{ promptId: 'anything', answer: 'ok' }]);
  });

  it('returns [] for null input, which the API reads as "clear my answers"', () => {
    expect(sanitizePromptAnswers(null)).toEqual([]);
    expect(sanitizePromptAnswers(undefined)).toEqual([]);
  });
});
