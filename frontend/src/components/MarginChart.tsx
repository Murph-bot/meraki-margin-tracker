import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { formatCents } from '../lib/format'

type Point = { date: string; net_cents: number }

export default function MarginChart({ data }: { data: Point[] }) {
  if (!data.length) {
    return (
      <section className="bg-white rounded-xl border p-6 shadow-sm">
        <h2 className="font-semibold mb-2">Margin trend</h2>
        <p className="text-sm text-gray-500">No synced transactions yet.</p>
      </section>
    )
  }

  const chartData = data.map(point => ({
    date: point.date.slice(5),
    net: point.net_cents / 100,
  }))

  return (
    <section className="bg-white rounded-xl border p-6 shadow-sm">
      <h2 className="font-semibold mb-4">Margin trend</h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value) => formatCents(Math.round(Number(value) * 100))} />
            <Line type="monotone" dataKey="net" stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
