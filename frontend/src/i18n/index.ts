import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import el from './locales/el.json'
import en from './locales/en.json'

export const LANG_STORAGE_KEY = 'meraki.lang'
export const SUPPORTED_LANGS = ['el', 'en'] as const
export type Lang = (typeof SUPPORTED_LANGS)[number]
export const DEFAULT_LANG: Lang = 'el'

export function isLang(value: unknown): value is Lang {
  return typeof value === 'string' && (SUPPORTED_LANGS as readonly string[]).includes(value)
}

// Browser language is deliberately ignored: Greek unless the user chose English.
function readStoredLang(): Lang {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY)
    if (isLang(stored)) return stored
  } catch {
    // storage unavailable (private mode etc.)
  }
  return DEFAULT_LANG
}

function syncDocument(lng: string) {
  if (typeof document === 'undefined') return
  document.documentElement.lang = lng
  document.title = i18n.t('meta.title')
  document
    .querySelector('meta[name="description"]')
    ?.setAttribute('content', i18n.t('meta.description'))
}

i18n.use(initReactI18next).init({
  resources: { el: { translation: el }, en: { translation: en } },
  lng: readStoredLang(),
  fallbackLng: DEFAULT_LANG,
  supportedLngs: [...SUPPORTED_LANGS],
  interpolation: { escapeValue: false },
  returnNull: false,
})

i18n.on('languageChanged', lng => {
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lng)
  } catch {
    // ignore
  }
  syncDocument(lng)
})
syncDocument(i18n.language)

export default i18n
