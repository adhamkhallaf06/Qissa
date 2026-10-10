import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

const REDIRECT_URI = 'http://localhost:8000/api/youtube/oauth/callback'

function Step({ number, title, children }: { number: number; title: string; children: ReactNode }) {
  return (
    <li className="guide-step">
      <span className="how-number">{number}</span>
      <div className="stack">
        <h2>{title}</h2>
        {children}
      </div>
    </li>
  )
}

export function ConnectGuide() {
  const { user } = useAuth()

  return (
    <main className="page guide">
      <header className="page-head">
        <h1>Connect your YouTube channel</h1>
        <p className="hint">
          About ten minutes, once. Qissa posts through a Google "OAuth client" that you create, so your channel stays under your control and you can revoke access at any time.
        </p>
      </header>

      <div className="card note">
        <strong>Already see a tick next to "Add your Google OAuth client file" in the studio?</strong>
        <p>Then a client file is already set up for this app. Skip to step 5 and just press Connect.</p>
      </div>

      <ol className="guide-steps">
        <Step number={1} title="Create a Google Cloud project">
          <p>
            Open <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer">Google Cloud Console</a> and sign in. In the project menu at the top, choose <b>New project</b>, give it any name (for example "Qissa"), and create it. Make sure it is the selected project for the next steps.
          </p>
        </Step>

        <Step number={2} title="Turn on the YouTube Data API">
          <p>
            Go to <b>APIs &amp; Services → Library</b>, search for <b>YouTube Data API v3</b>, open it and press <b>Enable</b>.
          </p>
        </Step>

        <Step number={3} title="Set up the consent screen">
          <p>
            Go to <b>APIs &amp; Services → OAuth consent screen</b> (Google may call it <b>Google Auth Platform</b>). Enter an app name and your email, and choose <b>External</b> as the audience.
          </p>
          <p>
            Under <b>Audience → Test users</b>, add the Google account that owns your YouTube channel. While the app is in "Testing", only the accounts listed there can sign in.
          </p>
        </Step>

        <Step number={4} title="Create the client and download the file">
          <p>
            Go to <b>APIs &amp; Services → Credentials → Create credentials → OAuth client ID</b>. Choose <b>Desktop app</b> as the application type and create it. Then press <b>Download JSON</b> — this is your <code>client_secret.json</code>.
          </p>
          <p className="hint">
            If you choose "Web application" instead, add this under "Authorized redirect URIs": <code>{REDIRECT_URI}</code>
          </p>
          <p className="hint">Treat this file like a password. Do not share it or commit it to a repository.</p>
        </Step>

        <Step number={5} title="Add the file in Qissa and connect">
          <p>
            Open the <Link to="/app">studio</Link> and scroll to <b>YouTube account</b>. Press <b>Choose file</b> and pick the JSON you downloaded, then press <b>Connect</b>.
          </p>
          <p>
            Google opens in a new tab. Sign in with the account that owns the channel, pick the channel if asked, and press <b>Allow</b>. If you see "Google hasn't verified this app", choose <b>Advanced → Go to (your app name)</b> — that warning appears because the client is your own and unreviewed.
          </p>
          <p>
            When the tab says "YouTube connected", close it. The studio now shows <b>Connected</b>, and you only repeat this if you disconnect.
          </p>
        </Step>
      </ol>

      <section className="card stack">
        <h2>If something goes wrong</h2>
        <dl className="faq">
          <dt>"Access blocked" or "access_denied"</dt>
          <dd>The Google account you signed in with is not a test user. Add it in step 3, then press Connect again.</dd>

          <dt>"redirect_uri_mismatch"</dt>
          <dd>Your client is a "Web application" without the redirect address. Add <code>{REDIRECT_URI}</code> to its Authorized redirect URIs, or create a Desktop app client instead.</dd>

          <dt>"This sign-in link has expired"</dt>
          <dd>The Connect button was pressed again, or the server restarted, before you finished. Go back to the studio and press Connect once more.</dd>

          <dt>It worked, then disconnected about a week later</dt>
          <dd>Google expires sign-ins after 7 days while the consent screen is in "Testing". Press Connect again, or publish the app on the consent screen page to make it last.</dd>

          <dt>Videos stay private on YouTube</dt>
          <dd>For Cloud projects that have not passed YouTube's API audit, Google keeps API uploads private. You can make each video public by hand in YouTube Studio, or apply for the audit in Google's API Services form.</dd>

          <dt>Uploads stop with a "quota" error</dt>
          <dd>New projects get a limited daily allowance of uploads from Google. It resets every day at midnight Pacific Time.</dd>
        </dl>
      </section>

      <div className="submit">
        <Link to={user ? '/app' : '/signup'} className="btn primary big">
          {user ? 'Back to the studio' : 'Create your account'}
        </Link>
      </div>
    </main>
  )
}
