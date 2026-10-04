import { describe, expect, it } from 'vitest'
import i18n from './index'
import el from './locales/el.json'
import { DETAIL_KEYS, apiErrorMessage } from './errors'

const apiError = (status: number, detail: unknown) => ({ response: { status, data: { detail } } })

describe('apiErrorMessage', () => {
  it('maps known backend details to Greek', () => {
    expect(apiErrorMessage(apiError(401, 'Invalid email or password'))).toBe(el.errors.invalidCredentials)
    expect(apiErrorMessage(apiError(429, 'Too many attempts'))).toBe(el.errors.tooManyAttempts)
    expect(apiErrorMessage(apiError(400, 'Stripe key rejected: boom'))).toBe(el.errors.stripeKeyRejected)
  })

  it('follows the active language', async () => {
    await i18n.changeLanguage('en')
    expect(apiErrorMessage(apiError(401, 'Invalid email or password'))).toBe('Incorrect email or password.')
  })

  it('maps FastAPI 422 validation errors', () => {
    const msg = apiErrorMessage(apiError(422, [{ loc: ['body', 'email'], msg: 'bad', type: 'value_error' }]))
    expect(msg).toContain(el.errors.fields.email)
    expect(apiErrorMessage(apiError(422, [{ loc: ['body', 'zzz'] }]))).toBe(el.errors.validation)
  })

  it('falls back by status, network error and generic', () => {
    expect(apiErrorMessage(apiError(500, 'whatever'))).toBe(el.errors.server)
    expect(apiErrorMessage(apiError(404, 'Something unknown'))).toBe(el.errors.notFound)
    expect(apiErrorMessage({ request: {}, code: 'ERR_NETWORK' })).toBe(el.errors.network)
    expect(apiErrorMessage(new Error('x'))).toBe(el.errors.generic)
    expect(apiErrorMessage(new Error('x'), 'auth.login.failed')).toBe(el.auth.login.failed)
  })

  it('only references existing keys', () => {
    for (const key of Object.values(DETAIL_KEYS)) expect(i18n.exists(key)).toBe(true)
  })
})
