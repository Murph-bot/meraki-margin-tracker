import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiClient } from '../api/client'
import { apiErrorMessage } from '../i18n/errors'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function Signup({ onLogin }: { onLogin: (token: string) => void }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const res = await apiClient.post('/auth/signup', { name, email, password })
      onLogin(res.data.token)
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'auth.signup.failed'))
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <LanguageSwitcher className="mb-6" />
      <h1 className="text-2xl font-bold mb-6">{t('auth.signup.title')}</h1>
      {error && <p className="text-red-600 mb-4" role="alert">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="text" placeholder={t('auth.fullName')} value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border rounded px-3 py-2" required aria-label={t('auth.fullName')} />
        <input type="email" placeholder={t('auth.email')} value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2" required aria-label={t('auth.email')} />
        <input type="password" placeholder={t('auth.passwordNew')} value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2" required minLength={8} aria-label={t('auth.password')} />
        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
          {t('auth.signup.submit')}
        </button>
      </form>
      <p className="mt-4 text-sm">{t('auth.signup.haveAccount')} <Link to="/login" className="text-blue-600">{t('auth.signup.loginLink')}</Link></p>
    </div>
  )
}
