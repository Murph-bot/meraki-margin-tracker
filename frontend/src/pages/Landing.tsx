import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function Landing() {
  const { t } = useTranslation()
  return (
    <div className="text-center mt-24">
      <LanguageSwitcher className="mb-8" />
      <h1 className="text-5xl font-bold mb-4">Μεράκι</h1>
      <p className="text-xl text-gray-600 mb-2">{t('landing.tagline')}</p>
      <p className="text-gray-500 mb-8 max-w-lg mx-auto">
        {t('landing.description')}
      </p>
      <Link to="/signup" className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg hover:bg-blue-700">
        {t('landing.cta')}
      </Link>
      <p className="text-xs text-gray-400 mt-2">{t('landing.note')}</p>
    </div>
  )
}
