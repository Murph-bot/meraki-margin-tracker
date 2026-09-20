import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import ExpenseForm from '../components/ExpenseForm'
import { formatCents } from '../lib/format'

type Expense = {
  id: number
  amount_cents: number
  category: string
  description: string
  date: string
}

export default function Expenses() {
  const queryClient = useQueryClient()
  const { data = [] } = useQuery({
    queryKey: ['expenses'],
    queryFn: async () => (await apiClient.get<Expense[]>('/expenses')).data,
  })

  const createMutation = useMutation({
    mutationFn: (payload: {
      amount_cents: number
      category: string
      description: string
      date: string
      recurring: boolean
      interval_days: number
    }) => apiClient.post('/expenses', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/expenses/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Expenses</h1>
      <ExpenseForm onSubmit={async payload => { await createMutation.mutateAsync(payload) }} />
      <ul className="space-y-2">
        {data.map(item => (
          <li key={item.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
            <div>
              <p className="font-medium">{formatCents(item.amount_cents)} · {item.category}</p>
              <p className="text-sm text-gray-500">{item.date} {item.description}</p>
            </div>
            <button type="button" onClick={() => deleteMutation.mutate(item.id)}
              className="text-sm text-red-600 hover:underline">Delete</button>
          </li>
        ))}
        {data.length === 0 && <p className="text-sm text-gray-500">No expenses yet.</p>}
      </ul>
    </div>
  )
}
