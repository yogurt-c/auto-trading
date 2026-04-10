import axios from 'axios'

const api = axios.create({
  baseURL: (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? '/api',
  timeout: 30_000,
})

// Request: Authorization 헤더 자동 삽입
api.interceptors.request.use(config => {
  const token = sessionStorage.getItem('auth_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Response: 401 수신 시 토큰 제거 + /login 리다이렉트
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      sessionStorage.removeItem('auth_token')
      sessionStorage.removeItem('app_configured')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default api
