import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, getToken, setToken, type Me } from './api'

type AuthContextValue = {
  me: Me | null
  loading: boolean
  login: (login: string, password: string) => Promise<Me>
  refresh: () => Promise<Me | null>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    api
      .me()
      .then(setMe)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (loginName: string, password: string) => {
    const token = await api.login(loginName, password)
    setToken(token.access_token)
    const profile = await api.me()
    setMe(profile)
    return profile
  }, [])

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null)
      return null
    }
    const profile = await api.me()
    setMe(profile)
    return profile
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setMe(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ me, loading, login, refresh, logout }),
    [loading, login, logout, me, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('AuthProvider missing')
  return ctx
}
