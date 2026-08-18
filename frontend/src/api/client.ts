// src/api/client.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token on request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pharmacast_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Intercept responses — handle 401 and log API errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url || ''

    // Log API errors (skip the /logs/write endpoint to avoid infinite loop)
    if (!url.includes('/logs/write')) {
      try {
        const stored = localStorage.getItem('pharmacast_user')
        let username = 'anonymous'
        let user_role = 'UNKNOWN'
        if (stored) {
          const u = JSON.parse(stored)
          username = u.username
          user_role = u.role
        }
        const status = error.response?.status
        const detail = error.response?.data?.detail || error.message || 'Unknown error'
        api.post('/logs/write', {
          event_type: 'API_ERROR',
          message: `API Error ${status ?? 'NETWORK'} on ${url}`,
          detail: String(detail).slice(0, 500),
          username,
          user_role,
          status: 'ERROR',
          user_agent: navigator.userAgent,
        }).catch(() => {})
      } catch {
        // Silent fail — interceptor must never throw
      }
    }

    if (error.response && error.response.status === 401) {
      console.warn('Session expired or unauthorized request. Clearing tokens and redirecting to login.')
      localStorage.removeItem('pharmacast_token')
      localStorage.removeItem('pharmacast_user')

      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
