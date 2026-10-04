import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiErrorMessage } from '../i18n/errors'

type Props = {
  onSubmit: (payload: { processor: string; api_key: string; label: string }) => Promise<void>
}

export default function ConnectionForm({ onSubmit }: Props) {
  const { t } = useTranslation()
  const [processor, setProcessor] = useState('stripe')
  const [apiKey, setApiKey] = useState('')
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onSubmit({ processor, api_key: apiKey, label })
      setApiKey('')
      setLabel('')
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'connections.saveFailed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="font-semibold">{t('connections.add')}</h2>
      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}
      <label className="block text-sm">
        {t('connections.processor')}
        <select value={processor} onChange={e => setProcessor(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" aria-label={t('connections.processor')}>
          <option value="stripe">{t('processors.stripe')}</option>
          <option value="viva">{t('processors.viva')}</option>
        </select>
      </label>
      <label className="block text-sm">
        {t('connections.label')}
        <input value={label} onChange={e => setLabel(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" placeholder={t('connections.labelPlaceholder')} aria-label={t('connections.label')} />
      </label>
      <label className="block text-sm">
        {t('connections.apiKey')}
        <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" required minLength={8} aria-label={t('connections.apiKeyAria')} />
      </label>
      <p className="text-xs text-gray-400">{t('connections.hint')}</p>
      <button type="submit" disabled={busy}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
        {busy ? t('common.saving') : t('connections.save')}
      </button>
    </form>
  )
}
