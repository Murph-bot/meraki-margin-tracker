import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGS, isLang } from '../i18n'

export default function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { t, i18n } = useTranslation()
  const active = isLang(i18n.language) ? i18n.language : 'el'

  return (
    <div role="group" aria-label={t('language.label')}
      className={`inline-flex border rounded overflow-hidden text-xs ${className}`}>
      {SUPPORTED_LANGS.map(lang => (
        <button key={lang} type="button" lang={lang}
          onClick={() => { void i18n.changeLanguage(lang) }}
          aria-pressed={active === lang}
          title={t(`language.${lang}`)}
          className={`px-2 py-1 ${active === lang ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
