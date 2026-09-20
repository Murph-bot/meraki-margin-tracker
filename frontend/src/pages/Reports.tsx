import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { formatCents } from '../lib/format'

type MonthlyRow = {
  month: string
  invoiced_cents: number
  fees_cents: number
  expenses_cents: number
  vat_cents: number
  income_tax_cents: number
  social_security_cents: number
  net_cents: number
}

type Benchmark = {
  profession: string
  city: string
  min_rate: number
  max_rate: number
  median_rate: number
}

export default function Reports() {
  const monthly = useQuery({
    queryKey: ['reports-monthly'],
    queryFn: async () => (await apiClient.get<MonthlyRow[]>('/reports/monthly')).data,
  })
  const benchmarks = useQuery({
    queryKey: ['benchmarks'],
    queryFn: async () => (await apiClient.get<Benchmark[]>('/benchmarks')).data,
  })

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold mb-4">Monthly breakdown</h1>
        {!monthly.data?.length && <p className="text-sm text-gray-500">No months to report yet.</p>}
        {!!monthly.data?.length && (
          <table className="w-full text-sm bg-white border rounded-xl overflow-hidden">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="p-3">Month</th>
                <th className="p-3 text-right">Invoiced</th>
                <th className="p-3 text-right">Fees</th>
                <th className="p-3 text-right">VAT</th>
                <th className="p-3 text-right">Expenses</th>
                <th className="p-3 text-right">Income tax</th>
                <th className="p-3 text-right">ΕΦΚΑ</th>
                <th className="p-3 text-right">Take-home</th>
              </tr>
            </thead>
            <tbody>
              {monthly.data.map(row => (
                <tr key={row.month} className="border-t">
                  <td className="p-3">{row.month}</td>
                  <td className="p-3 text-right">{formatCents(row.invoiced_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.fees_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.vat_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.expenses_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.income_tax_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.social_security_cents)}</td>
                  <td className="p-3 text-right">{formatCents(row.net_cents)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section>
        <h2 className="text-xl font-semibold mb-4">Greek rate benchmarks</h2>
        <ul className="space-y-2">
          {benchmarks.data?.map(item => (
            <li key={`${item.profession}-${item.city}`} className="bg-white border rounded-xl p-4">
              <p className="font-medium">{item.profession} · {item.city}</p>
              <p className="text-sm text-gray-600">
                €{item.min_rate}–€{item.max_rate}/hr · median €{item.median_rate}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
