/**
 * Pure input-validation utilities for the humanization form.
 *
 * Keeping this logic in plain JS makes it trivial to unit-test without
 * needing a browser or Svelte component harness.
 */

export const DEFAULT_MAX_CHARS = 5000;

export function validateHumanizeInput(text, maxChars = DEFAULT_MAX_CHARS) {
  const trimmed = text.trim();

  if (!trimmed) {
    return { ok: false, message: 'Please enter some text to humanize.' };
  }

  if (trimmed.length > maxChars) {
    return {
      ok: false,
      message: `Text is too long. Please keep it under ${maxChars.toLocaleString()} characters.`,
    };
  }

  return { ok: true, trimmed };
}
