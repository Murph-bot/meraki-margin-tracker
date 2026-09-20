import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import ConnectionForm from '../components/ConnectionForm'

type Connection = {
  id: number
  processor: string
  label: string
  last_synced_at: string | null
}

export default function Connections() {
  const queryClient = useQueryClient()
  const { data = [] } = useQuery({
    queryKey: ['connections'],
    queryFn: async () => (await apiClient.get<Connection[]>('/connections')).data,
  })

  const createMutation = useMutation({
    mutationFn: (payload: { processor: string; api_key: string; label: string }) =>
      apiClient.post('/connections', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  const syncMutation = useMutation({
    mutationFn: (id: number) => apiClient.post(`/connections/${id}/sync`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/connections/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['reports-monthly'] })
    },
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Connections</h1>
      <ConnectionForm onSubmit={async payload => { await createMutation.mutateAsync(payload) }} />
      <ul className="space-y-3">
        {data.map(item => (
          <li key={item.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
            <div>
              <p className="font-medium capitalize">{item.processor} {item.label && `· ${item.label}`}</p>
              <p className="text-xs text-gray-500">Last sync: {item.last_synced_at || 'never'}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => syncMutation.mutate(item.id)}
                className="text-sm px-3 py-1 border rounded hover:bg-gray-50">Refresh</button>
              <button type="button" onClick={() => deleteMutation.mutate(item.id)}
                className="text-sm px-3 py-1 text-red-600 hover:underline">Remove</button>
            </div>
          </li>
        ))}
        {data.length === 0 && <p className="text-sm text-gray-500">No processors connected yet.</p>}
      </ul>
    </div>
  )
}
