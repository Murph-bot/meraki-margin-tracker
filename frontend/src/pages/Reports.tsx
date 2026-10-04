import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { apiClient } from '../api/client'
import { apiErrorMessage } from '../i18n/errors'
import { formatCents, formatEuros, formatMonth } from '../lib/format'

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

const slug = (value: string) => value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')

export default function Reports() {
  const { t } = useTranslation()
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
        <h1 className="text-2xl font-bold mb-4">{t('reports.monthlyTitle')}</h1>
        {monthly.isLoading && <p className="text-sm text-gray-500">{t('common.loading')}</p>}
        {monthly.error && <p className="text-sm text-red-600" role="alert">{apiErrorMessage(monthly.error, 'reports.loadError')}</p>}
        {monthly.isSuccess && !monthly.data.length && <p className="text-sm text-gray-500">{t('reports.empty')}</p>}
        {!!monthly.data?.length && (
          <table className="w-full text-sm bg-white border rounded-xl overflow-hidden">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="p-3">{t('reports.columns.month')}</th>
                <th className="p-3 text-right">{t('reports.columns.invoiced')}</th>
                <th className="p-3 text-right">{t('reports.columns.fees')}</th>
                <th className="p-3 text-right">{t('reports.columns.vat')}</th>
                <th className="p-3 text-right">{t('reports.columns.expenses')}</th>
                <th className="p-3 text-right">{t('reports.columns.incomeTax')}</th>
                <th className="p-3 text-right">{t('reports.columns.efka')}</th>
                <th className="p-3 text-right">{t('reports.columns.takeHome')}</th>
              </tr>
            </thead>
            <tbody>
              {monthly.data.map(row => (
                <tr key={row.month} className="border-t">
                  <td className="p-3">{formatMonth(row.month)}</td>
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
        <h2 className="text-xl font-semibold mb-4">{t('reports.benchmarksTitle')}</h2>
        <ul className="space-y-2">
          {benchmarks.data?.map(item => (
            <li key={`${item.profession}-${item.city}`} className="bg-white border rounded-xl p-4">
              <p className="font-medium">{t(`reports.professions.${slug(item.profession)}`, { defaultValue: item.profession })} · {t(`reports.cities.${slug(item.city)}`, { defaultValue: item.city })}</p>
              <p className="text-sm text-gray-600">
                {t('reports.benchmarkRange', { min: formatEuros(item.min_rate), max: formatEuros(item.max_rate), median: formatEuros(item.median_rate) })}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
