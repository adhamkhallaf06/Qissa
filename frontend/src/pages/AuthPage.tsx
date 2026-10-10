import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { Field } from '../components/ui'

const MIN_PASSWORD = 8

export function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const signingUp = mode === 'signup'

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Where the user was headed before being asked to log in
  const next = (location.state as { from?: string } | null)?.from ?? '/app'

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (signingUp && password.length < MIN_PASSWORD) {
      setError(`Use at least ${MIN_PASSWORD} characters for your password.`)
      return
    }
    setError('')
    setBusy(true)
    try {
      if (signingUp) await auth.signup(name, email, password)
      else await auth.login(email, password)
      navigate(next, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page narrow">
      <form className="card stack" onSubmit={submit}>
        <header>
          <h1 className="auth-title">{signingUp ? 'Create your account' : 'Welcome back'}</h1>
          <p className="hint">{signingUp ? 'Start turning long videos into Shorts.' : 'Log in to get back to your videos.'}</p>
        </header>

        {signingUp && (
          <Field label="Name">
            <input type="text" required maxLength={80} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
        )}
        <Field label="Email">
          <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" hint={signingUp ? `At least ${MIN_PASSWORD} characters` : undefined}>
          <input
            type="password"
            required
            autoComplete={signingUp ? 'new-password' : 'current-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>

        {error && <p className="error" role="alert">{error}</p>}

        <button type="submit" className="btn primary big" disabled={busy}>
          {busy ? 'One moment…' : signingUp ? 'Create account' : 'Log in'}
        </button>

        <p className="hint center-text">
          {signingUp ? 'Already have an account? ' : 'New here? '}
          <Link to={signingUp ? '/login' : '/signup'} state={location.state}>
            {signingUp ? 'Log in' : 'Create an account'}
          </Link>
        </p>
      </form>
    </main>
  )
}
