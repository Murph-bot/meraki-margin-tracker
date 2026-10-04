import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useTranslation } from 'react-i18next'
import { formatCents, formatDate, formatDayMonth, formatNumber } from '../lib/format'

type Point = { date: string; net_cents: number }

export default function MarginChart({ data }: { data: Point[] }) {
  const { t } = useTranslation()
  if (!data.length) {
    return (
      <section className="bg-white rounded-xl border p-6 shadow-sm">
        <h2 className="font-semibold mb-2">{t('chart.title')}</h2>
        <p className="text-sm text-gray-500">{t('chart.empty')}</p>
      </section>
    )
  }

  const chartData = data.map(point => ({
    date: point.date,
    net: point.net_cents / 100,
  }))

  return (
    <section className="bg-white rounded-xl border p-6 shadow-sm">
      <h2 className="font-semibold mb-4">{t('chart.title')}</h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={formatDayMonth} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => formatNumber(v)} />
            <Tooltip labelFormatter={(label) => formatDate(String(label))}
              formatter={(value) => formatCents(Math.round(Number(value) * 100))} />
            <Legend />
            <Line type="monotone" dataKey="net" name={t('chart.series')} stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
