import i18n from '../i18n'

const INTL_LOCALES: Record<string, string> = { el: 'el-GR', en: 'en-IE' }

/** BCP-47 locale for the active UI language. */
export function currentLocale(): string {
  return INTL_LOCALES[i18n.language] ?? INTL_LOCALES.el
}

/**
 * Format a cent-based integer amount as EUR in the active locale.
 * el: 12345 -> "123,45 €"; en: 12345 -> "€123.45"
 */
export function formatCents(cents: number): string {
  return new Intl.NumberFormat(currentLocale(), {
    style: 'currency',
    currency: 'EUR',
  }).format(cents / 100)
}

/** Format a plain euro amount (not cents), e.g. hourly rates. Drops ".00". */
export function formatEuros(euros: number): string {
  return new Intl.NumberFormat(currentLocale(), {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: Number.isInteger(euros) ? 0 : 2,
  }).format(euros)
}

export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(currentLocale(), options).format(value)
}

/** Format a whole-number percentage (e.g. 83 -> "83%"). Pass 0-100 values. */
export function formatPercent(percent: number): string {
  return new Intl.NumberFormat(currentLocale(), {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(percent / 100)
}

/**
 * Format a cent-based integer amount as a plain decimal string.
 * Example: 12345 -> "123.45"
 */
export function centsToDecimal(cents: number): string {
  return (cents / 100).toFixed(2)
}

/**
 * Parse a Euro string back to cents.
 * Accepts `12.50` and Greek `12,50` (comma as decimal).
 * Example: "123.45" -> 12345
 */
export function parseEuros(value: string): number {
  const trimmed = value.trim().replace(/€/g, '').replace(/\s/g, '')
  const lastComma = trimmed.lastIndexOf(',')
  const lastDot = trimmed.lastIndexOf('.')
  const normalized = lastComma > lastDot
    ? trimmed.replace(/\./g, '').replace(',', '.')
    : trimmed.replace(/,/g, '')
  return Math.round(parseFloat(normalized) * 100)
}

export function localDateISO(now = new Date()): string {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// "YYYY-MM-DD" -> local-midnight Date (avoids the UTC shift of new Date(iso)).
function parseISODate(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return null
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

/** "2026-10-04" -> "4 Οκτ 2026" / "4 Oct 2026". Falls back to the input. */
export function formatDate(iso: string): string {
  const date = parseISODate(iso)
  if (!date) return iso
  return new Intl.DateTimeFormat(currentLocale(), {
    day: 'numeric', month: 'short', year: 'numeric',
  }).format(date)
}

/** "2026-10-04" -> "4 Οκτ" (chart axis). */
export function formatDayMonth(iso: string): string {
  const date = parseISODate(iso)
  if (!date) return iso
  return new Intl.DateTimeFormat(currentLocale(), { day: 'numeric', month: 'short' }).format(date)
}

/** "2026-10" -> "Οκτώβριος 2026" / "October 2026". Falls back to the input. */
export function formatMonth(ym: string): string {
  const m = /^(\d{4})-(\d{2})/.exec(ym)
  if (!m) return ym
  return new Intl.DateTimeFormat(currentLocale(), { month: 'long', year: 'numeric' })
    .format(new Date(Number(m[1]), Number(m[2]) - 1, 1))
}

/**
 * Backend timestamps come from SQLite datetime('now'): "YYYY-MM-DD HH:MM:SS" in UTC.
 * Rendered in Athens time.
 */
export function formatDateTime(value: string): string {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(value)
  const date = new Date(hasZone ? value : `${value.replace(' ', 'T')}Z`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(currentLocale(), {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Athens',
  }).format(date)
}
