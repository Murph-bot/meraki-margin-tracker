import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean }

const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('meraki_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined
    if (!original) {
      return Promise.reject(error)
    }
    const url = original.url || ''
    const skip = url.includes('/auth/login') || url.includes('/auth/signup') || url.includes('/auth/refresh')
    if (error.response?.status === 401 && !original._retry && !skip) {
      original._retry = true
      try {
        const res = await apiClient.post<{ token: string }>('/auth/refresh')
        localStorage.setItem('meraki_token', res.data.token)
        original.headers.Authorization = `Bearer ${res.data.token}`
        return apiClient.request(original)
      } catch {
        localStorage.removeItem('meraki_token')
      }
    }
    return Promise.reject(error)
  },
)

export { apiClient }
