import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './LanguageSwitcher'

export default function Navbar({ isLoggedIn, onLogout }: { isLoggedIn: boolean; onLogout: () => void }) {
  const { t } = useTranslation()
  return (
    <nav className="bg-white border-b shadow-sm" aria-label={t('nav.main')}>
      <div className="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold text-blue-600">Meraki</Link>
        <div className="flex gap-4 items-center">
          {isLoggedIn ? (
            <>
              <Link to="/dashboard" className="text-sm hover:text-blue-600">{t('nav.dashboard')}</Link>
              <Link to="/connections" className="text-sm hover:text-blue-600">{t('nav.connections')}</Link>
              <Link to="/expenses" className="text-sm hover:text-blue-600">{t('nav.expenses')}</Link>
              <Link to="/reports" className="text-sm hover:text-blue-600">{t('nav.reports')}</Link>
              <button type="button" onClick={onLogout} className="text-sm text-gray-500 hover:text-red-600" aria-label={t('nav.logout')}>{t('nav.logout')}</button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm hover:text-blue-600">{t('nav.login')}</Link>
              <Link to="/signup" className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">{t('nav.signup')}</Link>
            </>
          )}
          <LanguageSwitcher />
        </div>
      </div>
    </nav>
  )
}
