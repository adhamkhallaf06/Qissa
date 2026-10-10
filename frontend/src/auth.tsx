import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, type User } from './api'

interface AuthState {
  user: User | null
  /** True until the first "who am I" check finishes */
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => setUser(await api.login(email, password)), [])
  const signup = useCallback(
    async (name: string, email: string, password: string) => setUser(await api.signup(name, email, password)),
    [],
  )
  const logout = useCallback(async () => {
    await api.logout().catch(() => {})
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, login, signup, logout }), [user, loading, login, signup, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}
