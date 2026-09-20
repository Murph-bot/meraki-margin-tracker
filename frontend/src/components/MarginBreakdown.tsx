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
  const rows = [
    { label: 'Gross invoiced', value: props.invoicedCents },
    { label: 'VAT (24%, pass-through)', value: props.vatCents },
    { label: 'Processor fees', value: props.feesCents },
    { label: 'Expenses', value: props.expensesCents },
    { label: 'Income tax', value: props.incomeTaxCents },
    { label: 'ΕΦΚΑ + OAED', value: props.socialSecurityCents },
    { label: 'Tax prepayment (cash timing)', value: props.prepaymentCents },
    { label: 'Net take-home', value: props.netCents },
  ]

  return (
    <section className="bg-white rounded-xl border p-6 shadow-sm">
      <h2 className="font-semibold mb-4">Where the money goes</h2>
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
