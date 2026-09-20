import { formatCents } from '../lib/format'

type Props = {
  netCents: number
  invoicedCents: number
  keepPercent: number
  hourlyCents: number | null
}

export default function TakeHomeCard({
  netCents,
  invoicedCents,
  keepPercent,
  hourlyCents,
}: Props) {
  return (
    <section className="bg-white rounded-xl border p-6 shadow-sm">
      <p className="text-sm text-gray-500">Your true take-home this month</p>
      <p className="text-4xl font-bold mt-2">{formatCents(netCents)}</p>
      <p className="text-gray-500 mt-1">from {formatCents(invoicedCents)} invoiced</p>
      <div className="mt-4 h-2 bg-gray-100 rounded">
        <div
          className="h-2 bg-blue-600 rounded"
          style={{ width: `${Math.min(100, Math.max(0, keepPercent))}%` }}
        />
      </div>
      <p className="mt-3 text-sm">You keep <span className="font-semibold">{keepPercent}%</span> of what you invoice</p>
      {hourlyCents !== null && (
        <p className="text-sm text-gray-600 mt-1">{formatCents(hourlyCents)}/hr effective</p>
      )}
    </section>
  )
}
