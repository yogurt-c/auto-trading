import axios from 'axios'

const api = axios.create({
  baseURL: (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? '/api',
  timeout: 30_000,
})

export default api
