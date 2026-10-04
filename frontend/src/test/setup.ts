import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import i18n, { DEFAULT_LANG } from '../i18n'

beforeEach(async () => {
  localStorage.clear()
  await i18n.changeLanguage(DEFAULT_LANG)
  localStorage.clear()
})

afterEach(() => cleanup())
