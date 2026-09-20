import { useState } from 'react'

type Props = {
  onSubmit: (payload: { processor: string; api_key: string; label: string }) => Promise<void>
}

export default function ConnectionForm({ onSubmit }: Props) {
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
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(detail || 'Could not save connection')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-4 space-y-3">
      <h2 className="font-semibold">Add connection</h2>
      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}
      <label className="block text-sm">
        Processor
        <select value={processor} onChange={e => setProcessor(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" aria-label="Processor">
          <option value="stripe">Stripe</option>
          <option value="viva">Viva Wallet</option>
        </select>
      </label>
      <label className="block text-sm">
        Label
        <input value={label} onChange={e => setLabel(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" placeholder="Main account" aria-label="Label" />
      </label>
      <label className="block text-sm">
        Restricted API key
        <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
          className="w-full border rounded px-3 py-2 mt-1" required minLength={8} aria-label="API key" />
      </label>
      <p className="text-xs text-gray-400">Use a read-only Stripe restricted key. Keys are encrypted at rest.</p>
      <button type="submit" disabled={busy}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
        {busy ? 'Saving…' : 'Save connection'}
      </button>
    </form>
  )
}
