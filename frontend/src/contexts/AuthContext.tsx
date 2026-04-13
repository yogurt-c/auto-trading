import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/endpoints'

interface AuthContextValue {
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (password: string) => Promise<void>
  setSession: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('auth_token'))
  const [isLoading, setIsLoading] = useState(true)

  // 앱 초기화: 저장된 토큰 유효성 확인
  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    authApi
      .me()
      .then(() => setIsLoading(false))
      .catch(() => {
        sessionStorage.removeItem('auth_token')
        setToken(null)
        setIsLoading(false)
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const setSession = useCallback((accessToken: string) => {
    sessionStorage.setItem('auth_token', accessToken)
    sessionStorage.setItem('app_configured', 'true')
    setToken(accessToken)
  }, [])

  const login = useCallback(async (password: string) => {
    const data = await authApi.login(password)
    setSession(data.access_token)
  }, [setSession])

  const logout = useCallback(() => {
    sessionStorage.removeItem('auth_token')
    sessionStorage.removeItem('app_configured')
    setToken(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        setSession,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
