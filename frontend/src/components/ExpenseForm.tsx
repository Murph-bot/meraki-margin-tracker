import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { apiErrorMessage } from '../i18n/errors'
import { parseEuros, localDateISO } from '../lib/format'

const CATEGORIES = [
  'software',
  'hardware',
  'office',
  'travel',
  'professional_services',
  'other',
]

type Props = {
  onSubmit: (payload: {
    amount_cents: number
    category: string
    description: string
    date: string
    recurring: boolean
    interval_days: number
  }) => Promise<void>
}

export default function ExpenseForm({ onSubmit }: Props) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('other')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(() => localDateISO())
  const [recurring, setRecurring] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const amountCents = parseEuros(amount)
    if (!Number.isFinite(amountCents) || amountCents <= 0) {
      setError(t('expenses.invalidAmount'))
      return
    }
    setBusy(true)
    setError('')
    try {
      await onSubmit({
        amount_cents: amountCents,
        category,
        description,
        date,
        recurring,
        interval_days: recurring ? 30 : 0,
      })
      setAmount('')
      setDescription('')
    } catch (err) {
      setError(apiErrorMessage(err, 'expenses.saveFailed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="font-semibold">{t('expenses.add')}</h2>
      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}
      <input value={amount} onChange={e => setAmount(e.target.value)}
        placeholder={t('expenses.amountPlaceholder')} className="w-full border rounded px-3 py-2" required aria-label={t('expenses.amount')} />
      <select value={category} onChange={e => setCategory(e.target.value)}
        className="w-full border rounded px-3 py-2" aria-label={t('expenses.category')}>
        {CATEGORIES.map(item => (
          <option key={item} value={item}>{t(`expenses.categories.${item}`)}</option>
        ))}
      </select>
      <input value={description} onChange={e => setDescription(e.target.value)}
        placeholder={t('expenses.description')} className="w-full border rounded px-3 py-2" aria-label={t('expenses.description')} />
      <input type="date" value={date} onChange={e => setDate(e.target.value)}
        className="w-full border rounded px-3 py-2" required aria-label={t('expenses.date')} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={recurring} onChange={e => setRecurring(e.target.checked)}
          aria-label={t('expenses.recurring')} />
        {t('expenses.recurring')}
      </label>
      <button type="submit" disabled={busy}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
        {busy ? t('common.saving') : t('expenses.add')}
      </button>
    </form>
  )
}
