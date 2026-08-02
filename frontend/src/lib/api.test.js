import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { buildPayload, humanizeText } from './api.js'

const defaultParams = {
  text: 'hello',
  method: 'translation_chain',
  language: 'en',
  tier: 'standard',
}

describe('buildPayload', () => {
  it('creates the expected payload for plain text', () => {
    const payload = buildPayload(defaultParams)
    expect(payload).toEqual({
      text: 'hello',
      method: 'translation_chain',
      language: 'en',
      tier: 'standard',
    })
    expect(JSON.parse(JSON.stringify(payload))).toEqual(payload)
  })

  it('serializes text containing quotes correctly via JSON.stringify', () => {
    const payload = buildPayload({
      ...defaultParams,
      text: 'She said "hello" and then left.',
    })
    const serialized = JSON.stringify(payload)
    expect(serialized).toBe(
      '{"text":"She said \\"hello\\" and then left.","method":"translation_chain","language":"en","tier":"standard"}'
    )
    expect(JSON.parse(serialized).text).toBe('She said "hello" and then left.')
  })

  it('serializes text containing newlines correctly via JSON.stringify', () => {
    const payload = buildPayload({
      ...defaultParams,
      text: 'Line one\nLine two\r\nLine three',
    })
    const serialized = JSON.stringify(payload)
    expect(serialized).toContain('\\n')
    const parsed = JSON.parse(serialized)
    expect(parsed.text).toBe('Line one\nLine two\r\nLine three')
  })

  it('serializes text containing Unicode and emoji correctly', () => {
    const text = 'Hello world 🌍 café'
    const payload = buildPayload({ ...defaultParams, text })
    const serialized = JSON.stringify(payload)
    const parsed = JSON.parse(serialized)
    expect(parsed.text).toBe(text)
  })

  it('trims whitespace from the text field', () => {
    const payload = buildPayload({
      ...defaultParams,
      text: '   spaced out   ',
    })
    expect(payload.text).toBe('spaced out')
  })
})

describe('humanizeText response handling', () => {
  let fetchSpy

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function mockResponse({ ok = true, status = 200, statusText = 'OK', contentType = 'application/json', bodyText = '', json = null }) {
    return {
      ok,
      status,
      statusText,
      headers: {
        get: (name) => (name.toLowerCase() === 'content-type' ? contentType : null),
      },
      text: async () => bodyText,
      json: async () => (json !== null ? json : JSON.parse(bodyText)),
    }
  }

  it('resolves with parsed JSON on a successful JSON response', async () => {
    const response = mockResponse({
      bodyText: JSON.stringify({
        result: 'humanized hello',
        method: 'translation_chain',
        processing_time_ms: 42,
      }),
    })
    fetchSpy.mockResolvedValue(response)

    const data = await humanizeText(defaultParams)
    expect(data.result).toBe('humanized hello')
    expect(data.processing_time_ms).toBe(42)
    expect(fetchSpy).toHaveBeenCalledOnce()
    const [url, options] = fetchSpy.mock.calls[0]
    expect(url).toBe('/humanize')
    expect(options.method).toBe('POST')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body).text).toBe('hello')
  })

  it('throws a friendly error for an HTML 500 response', async () => {
    fetchSpy.mockResolvedValue(
      mockResponse({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        contentType: 'text/html; charset=utf-8',
        bodyText: '<html><body>Internal Server Error</body></html>',
      })
    )

    await expect(humanizeText(defaultParams)).rejects.toThrow(
      'Server returned 500 (Internal Server Error)'
    )
  })

  it('throws a friendly error for a non-JSON success response', async () => {
    fetchSpy.mockResolvedValue(
      mockResponse({
        ok: true,
        status: 200,
        contentType: 'text/plain',
        bodyText: 'unexpected plaintext',
      })
    )

    await expect(humanizeText(defaultParams)).rejects.toThrow(
      'Unexpected response format from server'
    )
  })

  it('uses the detail/message/error field from JSON errors', async () => {
    fetchSpy.mockResolvedValue(
      mockResponse({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        bodyText: JSON.stringify({ detail: 'Missing required field' }),
      })
    )

    await expect(humanizeText(defaultParams)).rejects.toThrow('Missing required field')
  })

  it('re-throws network errors without crashing', async () => {
    fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(humanizeText(defaultParams)).rejects.toThrow('Failed to fetch')
  })
})
