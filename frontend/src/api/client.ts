import axios, { AxiosError } from 'axios'

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

// The backend has no refresh token: /auth/refresh needs a still-valid JWT, so
// retrying a 401 through it can never succeed. Drop the stale token instead.
apiClient.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    const url = error.config?.url || ''
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/signup')
    if (error.response?.status === 401 && !isAuthCall) {
      localStorage.removeItem('meraki_token')
    }
    return Promise.reject(error)
  },
)

export { apiClient }
