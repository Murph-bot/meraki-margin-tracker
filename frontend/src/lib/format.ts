/**
 * Format a cent-based integer amount as a Euro string.
 * Example: 12345 -> "€123.45"
 */
export function formatCents(cents: number): string {
  const euros = cents / 100
  return `€${euros.toFixed(2)}`
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
