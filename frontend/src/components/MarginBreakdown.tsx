import { useTranslation } from 'react-i18next'
import { formatCents } from '../lib/format'

type Props = {
  invoicedCents: number
  feesCents: number
  expensesCents: number
  vatCents: number
  incomeTaxCents: number
  socialSecurityCents: number
  prepaymentCents: number
  netCents: number
}

export default function MarginBreakdown(props: Props) {
  const { t } = useTranslation()
  const rows = [
    { label: t('breakdown.gross'), value: props.invoicedCents },
    { label: t('breakdown.vat'), value: props.vatCents },
    { label: t('breakdown.fees'), value: props.feesCents },
    { label: t('breakdown.expenses'), value: props.expensesCents },
    { label: t('breakdown.incomeTax'), value: props.incomeTaxCents },
    { label: t('breakdown.socialSecurity'), value: props.socialSecurityCents },
    { label: t('breakdown.prepayment'), value: props.prepaymentCents },
    { label: t('breakdown.net'), value: props.netCents },
  ]

  return (
    <section className="bg-white rounded-xl border p-6 shadow-sm">
      <h2 className="font-semibold mb-4">{t('breakdown.title')}</h2>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(row => (
            <tr key={row.label} className="border-t">
              <td className="py-2 text-gray-600">{row.label}</td>
              <td className="py-2 text-right font-medium">{formatCents(row.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
