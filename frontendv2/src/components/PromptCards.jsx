import React from 'react';
import { useProfilePrompts, displayablePromptAnswers } from '../utils/prompts';

/**
 * P3FT.14 — read-only prompt cards (prompt text small and muted, answer larger).
 *
 * `answers`  — `[{ promptId, answer }]` from a user profile
 * `variant`  — 'detail' (UserDetailPage / ProfilePage) or 'compact' (Discover cards)
 * `max`      — cap the number of cards rendered
 *
 * Answers whose promptId is not in the catalogue are skipped, so a failed or
 * stale prompt fetch renders nothing rather than a blank/incorrect label.
 */
export default function PromptCards({ answers, variant = 'detail', max }) {
  const { prompts } = useProfilePrompts();
  let items = displayablePromptAnswers(answers, prompts);
  if (max != null) items = items.slice(0, max);
  if (items.length === 0) return null;

  return (
    <div className={`prompt-cards prompt-cards--${variant}`}>
      {items.map(item => (
        <div key={item.promptId} className="prompt-card">
          <p className="prompt-card-prompt">{item.text}</p>
          <p className="prompt-card-answer">{item.answer}</p>
        </div>
      ))}
    </div>
  );
}
