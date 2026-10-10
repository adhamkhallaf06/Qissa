import type { ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import { Layout } from './components/Layout'
import { AuthPage } from './pages/AuthPage'
import { Studio } from './pages/Studio'

function Loading() {
  return <main className="page center"><p className="hint">Loading…</p></main>
}

/** Pages that need an account: send visitors to log in, then back here. */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

/** Login / sign-up: skip straight to the app when already logged in. */
function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (user) return <Navigate to="/app" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="/login" element={<GuestOnly><AuthPage mode="login" /></GuestOnly>} />
        <Route path="/signup" element={<GuestOnly><AuthPage mode="signup" /></GuestOnly>} />
        <Route path="/app" element={<RequireAuth><Studio /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
