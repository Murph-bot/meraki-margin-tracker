import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiClient } from '../api/client'
import { apiErrorMessage } from '../i18n/errors'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const res = await apiClient.post('/auth/login', { email, password })
      onLogin(res.data.token)
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'auth.login.failed'))
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <LanguageSwitcher className="mb-6" />
      <h1 className="text-2xl font-bold mb-6">{t('auth.login.title')}</h1>
      {error && <p className="text-red-600 mb-4" role="alert">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block">
          <span className="sr-only">{t('auth.email')}</span>
          <input type="email" placeholder={t('auth.email')} value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border rounded px-3 py-2" required aria-label={t('auth.email')} />
        </label>
        <label className="block">
          <span className="sr-only">{t('auth.password')}</span>
          <input type="password" placeholder={t('auth.password')} value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full border rounded px-3 py-2" required aria-label={t('auth.password')} />
        </label>
        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
          {t('auth.login.submit')}
        </button>
      </form>
      <p className="mt-4 text-sm">{t('auth.login.noAccount')} <Link to="/signup" className="text-blue-600">{t('auth.login.signupLink')}</Link></p>
    </div>
  )
}
