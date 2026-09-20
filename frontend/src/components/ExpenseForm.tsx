import { useState } from 'react'
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
      setError('Enter a valid amount')
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
    } catch {
      setError('Could not save expense')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="font-semibold">Add expense</h2>
      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}
      <input value={amount} onChange={e => setAmount(e.target.value)}
        placeholder="Amount in EUR" className="w-full border rounded px-3 py-2" required aria-label="Amount" />
      <select value={category} onChange={e => setCategory(e.target.value)}
        className="w-full border rounded px-3 py-2" aria-label="Category">
        {CATEGORIES.map(item => (
          <option key={item} value={item}>{item.split('_').join(' ')}</option>
        ))}
      </select>
      <input value={description} onChange={e => setDescription(e.target.value)}
        placeholder="Description" className="w-full border rounded px-3 py-2" aria-label="Description" />
      <input type="date" value={date} onChange={e => setDate(e.target.value)}
        className="w-full border rounded px-3 py-2" required aria-label="Date" />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={recurring} onChange={e => setRecurring(e.target.checked)}
          aria-label="Recurring monthly" />
        Recurring monthly
      </label>
      <button type="submit" disabled={busy}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
        {busy ? 'Saving…' : 'Add expense'}
      </button>
    </form>
  )
}
