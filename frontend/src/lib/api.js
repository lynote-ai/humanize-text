/**
 * Hardened API helper for the Humanize Text frontend.
 *
 * Builds a JSON request body, checks the response status and Content-Type,
 * and only parses JSON for actual JSON responses. Text/HTML error pages
 * are read as text and surfaced as a friendly error message.
 */

const DEFAULT_ENDPOINT = '/humanize';

/**
 * Build the request payload object from the form values.
 *
 * The payload is a plain object and is stringified with the standard
 * `JSON.stringify()` right before sending, so quotes, newlines, and
 * Unicode are handled automatically.
 *
 * @param {Object} params
 * @param {string} params.text
 * @param {string} params.method
 * @param {string} params.language
 * @param {string} [params.tier='standard']
 * @returns {{ text: string, method: string, language: string, tier: string }}
 */
export function buildPayload({ text, method, language, tier = 'standard' }) {
  return {
    text: text.trim(),
    method,
    language,
    tier,
  };
}

/**
 * POST the humanize request to the FastAPI backend.
 *
 * @param {Object} params
 * @param {string} params.text
 * @param {string} params.method
 * @param {string} params.language
 * @param {string} [params.tier='standard']
 * @returns {Promise<Object>} Parsed JSON response.
 * @throws {Error} On network failure, non-OK status, or non-JSON response.
 */
export async function humanizeText({ text, method, language, tier = 'standard' }) {
  const payload = buildPayload({ text, method, language, tier });

  // Allow overriding the API endpoint in dev/test environments.
  const endpoint = import.meta.env?.VITE_API_URL ?? DEFAULT_ENDPOINT;

  console.log('[humanize] sending payload:', payload);

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.toLowerCase().includes('application/json');

  console.log('[humanize] response status:', response.status, 'content-type:', contentType || '(none)');

  if (!response.ok) {
    if (isJson) {
      const data = await response.json();
      console.error('[humanize] JSON error response:', data);
      const message =
        data.detail || data.message || data.error || `Request failed (${response.status})`;
      throw new Error(message);
    }

    const rawText = await response.text();
    console.error('[humanize] non-JSON error response:', rawText.slice(0, 1000));
    throw new Error(
      `Server returned ${response.status} (${response.statusText}). ` +
        'The backend may have crashed or returned an HTML error page.'
    );
  }

  if (!isJson) {
    const rawText = await response.text();
    console.error('[humanize] unexpected non-JSON success response:', rawText.slice(0, 1000));
    throw new Error('Unexpected response format from server. Expected JSON.');
  }

  return response.json();
}
