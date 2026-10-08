import React from 'react';
import {
  useProfilePrompts,
  availablePrompts,
  MAX_PROMPT_ANSWERS,
  PROMPT_ANSWER_MAX_LENGTH,
} from '../utils/prompts';

/**
 * P3FT.14 — shared prompt-answer editor used by SignupPage and ProfilePage.
 *
 * `value`    — `[{ promptId, answer }]` (max 3, no duplicate promptId)
 * `onChange` — called with the next array on every edit
 * `inputClass` — lets each host page reuse its own input styling class
 *
 * Renders nothing at all when the prompt catalogue is unavailable, so a failed
 * `GET /api/profile-prompts` degrades to "hidden" instead of breaking the page.
 */
export default function PromptAnswersEditor({ value, onChange, inputClass = 'form-input' }) {
  const { prompts, ready } = useProfilePrompts();
  const answers = Array.isArray(value) ? value : [];

  if (!ready || prompts.length === 0) return null;

  const setAt = (index, patch) =>
    onChange(answers.map((a, i) => (i === index ? { ...a, ...patch } : a)));

  const removeAt = (index) => onChange(answers.filter((_, i) => i !== index));

  const move = (index, delta) => {
    const target = index + delta;
    if (target < 0 || target >= answers.length) return;
    const next = [...answers];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  const unused = availablePrompts(prompts, answers);
  const canAdd = answers.length < MAX_PROMPT_ANSWERS && unused.length > 0;

  const addRow = () => {
    if (!canAdd) return;
    onChange([...answers, { promptId: unused[0].id, answer: '' }]);
  };

  return (
    <div className="prompt-editor">
      {answers.map((a, i) => {
        const options = availablePrompts(prompts, answers, a.promptId);
        const len = (a.answer || '').length;
        return (
          <div key={`${a.promptId}-${i}`} className="prompt-editor-row">
            <div className="prompt-editor-row-head">
              <select
                className={inputClass}
                value={a.promptId}
                onChange={e => setAt(i, { promptId: e.target.value })}
                aria-label={`Prompt ${i + 1}`}
              >
                {options.map(p => <option key={p.id} value={p.id}>{p.text}</option>)}
              </select>
              <div className="prompt-editor-row-actions">
                <button
                  type="button"
                  className="prompt-editor-icon-btn"
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  aria-label="Move prompt up"
                  title="Move up"
                >↑</button>
                <button
                  type="button"
                  className="prompt-editor-icon-btn"
                  onClick={() => move(i, 1)}
                  disabled={i === answers.length - 1}
                  aria-label="Move prompt down"
                  title="Move down"
                >↓</button>
                <button
                  type="button"
                  className="prompt-editor-icon-btn prompt-editor-icon-btn--danger"
                  onClick={() => removeAt(i)}
                  aria-label="Remove prompt"
                  title="Remove"
                >✕</button>
              </div>
            </div>
            <textarea
              className={`${inputClass} prompt-editor-textarea`}
              value={a.answer || ''}
              maxLength={PROMPT_ANSWER_MAX_LENGTH}
              placeholder="Your answer…"
              onChange={e => setAt(i, { answer: e.target.value })}
              aria-label={`Answer to prompt ${i + 1}`}
            />
            <p className={`prompt-editor-count ${len >= PROMPT_ANSWER_MAX_LENGTH ? 'prompt-editor-count--max' : ''}`}>
              {len}/{PROMPT_ANSWER_MAX_LENGTH}
            </p>
          </div>
        );
      })}

      {canAdd ? (
        <button type="button" className="prompt-editor-add-btn" onClick={addRow}>
          + Add a prompt
        </button>
      ) : (
        answers.length >= MAX_PROMPT_ANSWERS && (
          <p className="prompt-editor-hint">
            You've used all {MAX_PROMPT_ANSWERS} prompts. Remove one to swap it out.
          </p>
        )
      )}
    </div>
  );
}
