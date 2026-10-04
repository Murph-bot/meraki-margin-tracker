import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { apiClient } from '../api/client'
import { apiErrorMessage } from '../i18n/errors'
import { formatDateTime } from '../lib/format'
import ConnectionForm from '../components/ConnectionForm'

type Connection = {
  id: number
  processor: string
  label: string
  last_synced_at: string | null
}

export default function Connections() {
  const { t } = useTranslation()
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

  const actionError = syncMutation.error
    ? apiErrorMessage(syncMutation.error, 'connections.syncFailed')
    : deleteMutation.error
      ? apiErrorMessage(deleteMutation.error, 'connections.removeFailed')
      : ''

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('connections.title')}</h1>
      {actionError && <p className="text-red-600 text-sm" role="alert">{actionError}</p>}
      <ConnectionForm onSubmit={async payload => { await createMutation.mutateAsync(payload) }} />
      <ul className="space-y-3">
        {data.map(item => (
          <li key={item.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
            <div>
              <p className="font-medium">{t(`processors.${item.processor}`, { defaultValue: item.processor })} {item.label && `· ${item.label}`}</p>
              <p className="text-xs text-gray-500">{t('connections.lastSync', { when: item.last_synced_at ? formatDateTime(item.last_synced_at) : t('common.never') })}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => syncMutation.mutate(item.id)}
                className="text-sm px-3 py-1 border rounded hover:bg-gray-50">{t('common.refresh')}</button>
              <button type="button" onClick={() => deleteMutation.mutate(item.id)}
                className="text-sm px-3 py-1 text-red-600 hover:underline">{t('common.remove')}</button>
            </div>
          </li>
        ))}
        {data.length === 0 && <p className="text-sm text-gray-500">{t('connections.empty')}</p>}
      </ul>
    </div>
  )
}
