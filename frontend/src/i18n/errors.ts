import i18n from './index'

/** Exact backend `detail` strings -> i18n keys under "errors.*". */
export const DETAIL_KEYS: Record<string, string> = {
  'Too many attempts': 'errors.tooManyAttempts',
  'Registration failed': 'errors.registrationFailed',
  'Invalid email or password': 'errors.invalidCredentials',
  'Invalid token': 'errors.sessionExpired',
  'User not found': 'errors.userNotFound',
  'Expense not found': 'errors.expenseNotFound',
  'Connection not found': 'errors.connectionNotFound',
  'Viva Wallet sync is not available in MVP': 'errors.vivaNotAvailable',
}

const STATUS_KEYS: Record<number, string> = {
  400: 'errors.badRequest',
  401: 'errors.unauthorized',
  403: 'errors.forbidden',
  404: 'errors.notFound',
  409: 'errors.conflict',
  422: 'errors.validation',
  429: 'errors.tooManyRequests',
  501: 'errors.notImplemented',
}

type ApiErrorLike = {
  response?: { status?: number; data?: { detail?: unknown } }
  request?: unknown
  code?: string
}

type ValidationItem = { loc?: unknown[]; type?: string; msg?: string }

const FIELD_KEYS: Record<string, string> = {
  email: 'errors.fields.email',
  password: 'errors.fields.password',
  name: 'errors.fields.name',
  api_key: 'errors.fields.apiKey',
  label: 'errors.fields.label',
  amount_cents: 'errors.fields.amount',
  category: 'errors.fields.category',
  description: 'errors.fields.description',
  date: 'errors.fields.date',
}

function validationMessage(items: ValidationItem[]): string {
  const first = items[0]
  const field = first && Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : ''
  const fieldKey = FIELD_KEYS[field]
  if (fieldKey && i18n.exists(fieldKey)) {
    return i18n.t('errors.validationField', { field: i18n.t(fieldKey) })
  }
  return i18n.t('errors.validation')
}

/**
 * Turn any thrown API/network error into a user-facing message in the active
 * language. `fallbackKey` is used when nothing more specific is known.
 */
export function apiErrorMessage(err: unknown, fallbackKey = 'errors.generic'): string {
  const e = (err ?? {}) as ApiErrorLike
  const status = e.response?.status
  const detail = e.response?.data?.detail

  if (typeof detail === 'string') {
    const key = DETAIL_KEYS[detail]
    if (key) return i18n.t(key)
    const stripe = /^Stripe key rejected:/.exec(detail)
    if (stripe) return i18n.t('errors.stripeKeyRejected')
  }
  if (Array.isArray(detail)) return validationMessage(detail as ValidationItem[])
  if (status !== undefined) {
    const key = STATUS_KEYS[status]
    if (key) return i18n.t(key)
    if (status >= 500) return i18n.t('errors.server')
    return i18n.t(fallbackKey)
  }
  // No response at all: network down / timeout / CORS.
  if (e.request !== undefined || e.code === 'ERR_NETWORK' || e.code === 'ECONNABORTED') {
    return i18n.t('errors.network')
  }
  return i18n.t(fallbackKey)
}
