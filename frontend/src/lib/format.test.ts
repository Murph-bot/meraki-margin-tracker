import { describe, expect, it } from 'vitest'
import i18n from '../i18n'
import { formatCents, formatDate, formatMonth, formatPercent } from './format'

const norm = (s: string) => s.replace(/[  ]/g, ' ')

describe('format (el default)', () => {
  it('formats currency the Greek way', () => {
    const out = norm(formatCents(123456))
    expect(out).toContain('1.234,56')
    expect(out).toContain('€')
    expect(out).toBe('1.234,56 €')
  })

  it('formats percentages and dates in Greek', () => {
    expect(norm(formatPercent(83.5))).toBe('83,5%')
    expect(formatMonth('2026-10')).toMatch(/Οκτώβριος 2026/)
    expect(formatDate('2026-10-04')).toMatch(/^4 Οκτ/)
  })

  it('switches to English formatting, still EUR', async () => {
    await i18n.changeLanguage('en')
    expect(norm(formatCents(123456))).toBe('€1,234.56')
    expect(formatMonth('2026-10')).toBe('October 2026')
  })
})
