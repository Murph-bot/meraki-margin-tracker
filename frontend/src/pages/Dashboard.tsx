import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { apiClient } from '../api/client'
import { apiErrorMessage } from '../i18n/errors'
import { formatCents } from '../lib/format'
import TakeHomeCard from '../components/TakeHomeCard'
import MarginBreakdown from '../components/MarginBreakdown'
import MarginChart from '../components/MarginChart'

type DashboardData = {
  invoiced_cents: number
  fees_cents: number
  expenses_cents: number
  income_tax_cents: number
  tax_prepayment_cents: number
  social_security_cents: number
  vat_cents: number
  net_cents: number
  keep_percent: number
  effective_hourly_cents: number | null
  trend: { date: string; net_cents: number }[]
  missing_processors: string[]
  disclaimer: string
}

type Profile = {
  efka_category: number
  years_active: number
  charges_vat: boolean
}

// Monthly EFKA contribution per category, in cents.
const EFKA_CATEGORIES: [number, number][] = [
  [1, 25077], [2, 30093], [3, 36063], [4, 43347], [5, 51945], [6, 67587],
]

export default function Dashboard() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [hours, setHours] = useState(0)
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', hours],
    queryFn: async () => (
      await apiClient.get<DashboardData>('/dashboard', { params: { hours } })
    ).data,
  })
  const profile = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await apiClient.get<Profile>('/auth/me')).data,
  })
  const updateProfile = useMutation({
    mutationFn: (payload: Partial<Profile>) => apiClient.patch('/auth/me', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })
  const refreshSync = useMutation({
    mutationFn: async () => {
      const conns = (await apiClient.get<{ id: number }[]>('/connections')).data
      for (const conn of conns) {
        try {
          await apiClient.post(`/connections/${conn.id}/sync`)
        } catch {
          continue
        }
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  if (isLoading) {
    return <p className="text-gray-500">{t('dashboard.loading')}</p>
  }

  if (error || !data) {
    return (
      <p className="text-red-600" role="alert">
        {error ? apiErrorMessage(error, 'dashboard.loadError') : t('dashboard.loadError')}
      </p>
    )
  }

  return (
    <div className="space-y-6">
      <TakeHomeCard
        netCents={data.net_cents}
        invoicedCents={data.invoiced_cents}
        keepPercent={data.keep_percent}
        hourlyCents={data.effective_hourly_cents}
      />
      <div className="bg-white border rounded-xl p-4 flex flex-wrap gap-4 items-center text-sm">
        <label>
          {t('dashboard.efkaCategory')}
          <select
            className="ml-2 border rounded px-2 py-1"
            aria-label={t('dashboard.efkaCategoryAria')}
            value={profile.data?.efka_category ?? 1}
            onChange={e => updateProfile.mutate({ efka_category: Number(e.target.value) })}
          >
            {EFKA_CATEGORIES.map(([id, cents]) => (
              <option key={id} value={id}>{id} — {formatCents(cents)}{t('common.perMonth')}</option>
            ))}
          </select>
        </label>
        <label>
          {t('dashboard.yearsActive')}
          <input
            type="number"
            min={1}
            max={50}
            className="ml-2 border rounded px-2 py-1 w-20"
            aria-label={t('dashboard.yearsActive')}
            value={profile.data?.years_active ?? 1}
            onChange={e => {
              const years = Number(e.target.value)
              if (Number.isInteger(years) && years >= 1 && years <= 50) {
                updateProfile.mutate({ years_active: years })
              }
            }}
          />
        </label>
        <label>
          {t('dashboard.hoursThisMonth')}
          <input
            type="number"
            min={0}
            className="ml-2 border rounded px-2 py-1 w-20"
            aria-label={t('dashboard.hoursAria')}
            value={hours}
            onChange={e => setHours(Number(e.target.value) || 0)}
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            aria-label={t('dashboard.chargeVatAria')}
            checked={profile.data?.charges_vat ?? false}
            onChange={e => updateProfile.mutate({ charges_vat: e.target.checked })}
          />
          {t('dashboard.chargeVat')}
        </label>
        <button
          type="button"
          className="ml-auto border rounded px-3 py-1 hover:bg-gray-50 disabled:opacity-50"
          aria-label={t('dashboard.refreshAria')}
          onClick={() => refreshSync.mutate()}
          disabled={refreshSync.isPending}
        >
          {refreshSync.isPending ? t('common.refreshing') : t('common.refresh')}
        </button>
      </div>
      <MarginBreakdown
        invoicedCents={data.invoiced_cents}
        feesCents={data.fees_cents}
        expensesCents={data.expenses_cents}
        vatCents={data.vat_cents}
        incomeTaxCents={data.income_tax_cents}
        socialSecurityCents={data.social_security_cents}
        prepaymentCents={data.tax_prepayment_cents}
        netCents={data.net_cents}
      />
      <MarginChart data={data.trend} />
      {data.missing_processors.length > 0 && (
        <p className="text-sm text-amber-700">
          {t('dashboard.missingConnections', {
            count: data.missing_processors.length,
            list: data.missing_processors.map(p => t(`processors.${p}`, { defaultValue: p })).join(' | '),
          })}{' '}
          <Link to="/connections" className="underline">{t('dashboard.connectProcessor')}</Link>
        </p>
      )}
      <p className="text-xs text-gray-400">{t('dashboard.disclaimer')}</p>
    </div>
  )
}
