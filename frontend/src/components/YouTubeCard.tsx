import { useEffect, useRef, useState } from 'react'
import { api, type YouTubeStatus } from '../api'
import { Card } from './ui'

export function YouTubeCard({ status, onStatus }: {
  status: YouTubeStatus | null
  onStatus: (status: YouTubeStatus) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [error, setError] = useState('')
  const [waiting, setWaiting] = useState(false)

  // While the Google tab is open, poll until the backend has the token
  useEffect(() => {
    if (!waiting) return
    const timer = setInterval(async () => {
      try {
        const next = await api.youtubeStatus()
        onStatus(next)
        if (next.connected) setWaiting(false)
      } catch {
        // keep polling
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [waiting, onStatus])

  const run = async (action: () => Promise<void>) => {
    setError('')
    try {
      await action()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const connect = () => run(async () => {
    const { auth_url } = await api.youtubeConnect()
    window.open(auth_url, '_blank', 'noopener')
    setWaiting(true)
  })

  const pill = !status ? <span className="pill">Checking…</span>
    : status.connected ? <span className="pill ok">Connected</span>
    : <span className="pill warn">Not connected</span>

  return (
    <Card step={5} title="YouTube account" aside={pill}>
      <div className="stack">
        <input
          ref={input}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = ''
            if (file) run(async () => onStatus(await api.uploadClientSecret(file)))
          }}
        />

        <ol className="steps">
          <li className={status?.has_client_secret ? 'done' : ''}>
            <div>
              <strong>Add your Google OAuth client file</strong>
              <p className="hint">
                The <code>client_secret.json</code> from Google Cloud Console → APIs &amp; Services → Credentials, with the YouTube Data API v3 enabled. It stays on the machine running the backend.
              </p>
            </div>
            <button type="button" className="btn" onClick={() => input.current?.click()}>
              {status?.has_client_secret ? 'Replace file' : 'Choose file'}
            </button>
          </li>
          <li className={status?.connected ? 'done' : ''}>
            <div>
              <strong>Sign in with the channel you want to post to</strong>
              <p className="hint">
                {waiting ? 'Finish signing in on the Google tab that just opened…' : 'Opens Google in a new tab. You only do this once.'}
              </p>
            </div>
            {status?.connected ? (
              <button type="button" className="btn ghost" onClick={() => run(async () => onStatus(await api.youtubeDisconnect()))}>Disconnect</button>
            ) : (
              <button type="button" className="btn primary" disabled={!status?.has_client_secret} onClick={connect}>Connect</button>
            )}
          </li>
        </ol>

        {error && <p className="error" role="alert">{error}</p>}
      </div>
    </Card>
  )
}
