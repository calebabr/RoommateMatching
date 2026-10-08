// P3FT.14 — prompt-style profile answers.
//
// The curated prompt list lives on the BACKEND and is served by
// `GET /api/profile-prompts` as `[{ id, text }]`.  It is the single source of
// truth: nothing in the frontend hardcodes prompt ids or prompt copy, because a
// second copy would drift silently and render blank or wrong prompt text.
//
// The list is static, so it is fetched at most once per page load and cached in
// module scope.  Every consumer degrades to "render nothing" when the fetch
// fails — a prompts outage must never break the profile pages.

import { useEffect, useState } from 'react';
import { getProfilePrompts } from '../services/api';

export const MAX_PROMPT_ANSWERS = 3;
export const PROMPT_ANSWER_MAX_LENGTH = 150;

let _cache = null;     // ProfilePrompt[] once a fetch has succeeded
let _inflight = null;  // de-dupes concurrent callers

/** Accepts the documented `[{id, text}]` payload and tolerates `{prompts: [...]}`. */
const normalize = (raw) => {
  const list = Array.isArray(raw)
    ? raw
    : Array.isArray(raw?.prompts) ? raw.prompts : [];
  return list
    .map(p => ({ id: String(p?.id ?? ''), text: String(p?.text ?? '') }))
    .filter(p => p.id && p.text);
};

/**
 * Resolve the prompt catalogue. Always resolves — never rejects.
 * A failed fetch resolves to `[]` and is NOT cached, so a later mount retries.
 */
export function loadProfilePrompts() {
  if (_cache) return Promise.resolve(_cache);
  if (!_inflight) {
    _inflight = getProfilePrompts()
      .then((raw) => {
        const list = normalize(raw);
        if (list.length) _cache = list;
        return list;
      })
      .catch(() => [])
      .finally(() => { _inflight = null; });
  }
  return _inflight;
}

/** Test/debug helper — drops the module-scope cache. */
export function resetProfilePromptsCache() {
  _cache = null;
  _inflight = null;
}

/**
 * `{ prompts, ready }` — `ready` flips true once the fetch settles, whether it
 * succeeded or not, so callers can distinguish "still loading" from "no prompts".
 */
export function useProfilePrompts() {
  const [prompts, setPrompts] = useState(() => _cache || []);
  const [ready, setReady] = useState(() => !!_cache);

  useEffect(() => {
    if (_cache) { setPrompts(_cache); setReady(true); return; }
    let active = true;
    loadProfilePrompts().then((list) => {
      if (!active) return;
      setPrompts(list);
      setReady(true);
    });
    return () => { active = false; };
  }, []);

  return { prompts, ready };
}

/** Prompt copy for an id, or '' when the catalogue does not know that id. */
export const promptTextFor = (prompts, promptId) =>
  (prompts || []).find(p => p.id === promptId)?.text || '';

/** Prompts the user has not answered yet (plus `keepId`, for an open editor row). */
export const availablePrompts = (prompts, answers, keepId = null) => {
  const used = new Set((answers || []).map(a => a.promptId));
  return (prompts || []).filter(p => !used.has(p.id) || p.id === keepId);
};

/**
 * Normalize editor state into the wire shape the API accepts:
 * trimmed, length-capped, no blanks, no duplicate `promptId`, at most 3.
 * `prompts` (optional) restricts ids to the catalogue.
 */
export const sanitizePromptAnswers = (answers, prompts = null) => {
  const known = prompts ? new Set(prompts.map(p => p.id)) : null;
  const seen = new Set();
  const out = [];
  for (const a of answers || []) {
    const promptId = String(a?.promptId || '');
    const answer = String(a?.answer || '').trim().slice(0, PROMPT_ANSWER_MAX_LENGTH);
    if (!promptId || !answer) continue;
    if (known && !known.has(promptId)) continue;
    if (seen.has(promptId)) continue;
    seen.add(promptId);
    out.push({ promptId, answer });
    if (out.length >= MAX_PROMPT_ANSWERS) break;
  }
  return out;
};

/** Only the answers whose prompt text we can actually render. */
export const displayablePromptAnswers = (answers, prompts) =>
  (answers || [])
    .map(a => ({ promptId: a?.promptId, answer: a?.answer, text: promptTextFor(prompts, a?.promptId) }))
    .filter(a => a.text && a.answer);
