import { describe, it, expect } from 'vitest'
import { validateHumanizeInput } from './validation.js'

describe('validateHumanizeInput', () => {
  it('accepts plain text and returns the trimmed value', () => {
    const result = validateHumanizeInput('  hello world  ')
    expect(result).toEqual({
      ok: true,
      trimmed: 'hello world',
    })
  })

  it('rejects empty input', () => {
    const result = validateHumanizeInput('')
    expect(result.ok).toBe(false)
    expect(result.message).toMatch(/enter some text/i)
  })

  it('rejects whitespace-only input', () => {
    const result = validateHumanizeInput('   \n\t  ')
    expect(result.ok).toBe(false)
    expect(result.message).toMatch(/enter some text/i)
  })

  it('rejects input that exceeds the character limit', () => {
    const long = 'a'.repeat(5001)
    const result = validateHumanizeInput(long)
    expect(result.ok).toBe(false)
    expect(result.message).toMatch(/too long/i)
  })

  it('respects a custom max length', () => {
    const result = validateHumanizeInput('abc', 2)
    expect(result.ok).toBe(false)
    expect(result.message).toMatch(/too long/i)
  })
})
