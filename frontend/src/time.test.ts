import { describe, expect, it } from 'vitest'
import { formatPacific, pacificInputToISO } from './time'

describe('pacificInputToISO', () => {
  it('reads winter times as PST (UTC-8)', () => {
    expect(pacificInputToISO('2026-12-12T11:00')).toBe('2026-12-12T19:00:00.000Z')
  })

  it('reads summer times as PDT (UTC-7)', () => {
    expect(pacificInputToISO('2027-06-01T11:00')).toBe('2027-06-01T18:00:00.000Z')
  })

  it('handles the evening that crosses midnight UTC', () => {
    expect(pacificInputToISO('2026-12-12T22:30')).toBe('2026-12-13T06:30:00.000Z')
  })

  it('handles the morning after clocks go back (Nov 1, 2026)', () => {
    expect(pacificInputToISO('2026-11-01T09:00')).toBe('2026-11-01T17:00:00.000Z')
  })
})

describe('formatPacific', () => {
  it('shows UTC instants in Pacific time', () => {
    expect(formatPacific('2026-12-12T16:10:00Z')).toBe('Sat, Dec 12, 8:10 AM')
  })
})
