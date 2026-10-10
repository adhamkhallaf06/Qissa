import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

const STEPS = [
  ['Upload', 'Drop in one long video — a lecture, a podcast, a stream.'],
  ['Cut', 'It is sliced into Short-length clips and reframed to vertical 9:16.'],
  ['Caption', 'Speech is transcribed and burned in, styled the way you choose.'],
  ['Schedule', 'Clips go to your YouTube channel and publish at the times you set.'],
]

const FEATURES = [
  ['Captions that look like yours', 'Pick the font, size, colors, outline or solid box, position, and how many words appear at once — with a live preview.'],
  ['Many languages', 'Arabic, English and more, or let it detect the language for you. Right-to-left text is handled.'],
  ['A posting schedule, not a chore', 'Choose daily time slots and a timezone. Clips fill the slots day after day until they run out.'],
  ['Titles and hashtags once', 'Write a title and your hashtags one time; every clip gets them, numbered if you like.'],
  ['No dead air', 'Clips that are mostly silence are dropped before they ever reach your channel.'],
  ['Preview before you post', 'Turn uploading off to just process and watch the clips, then decide.'],
]

/** A long video strip being cut into three vertical clips. Decorative. */
function CutDiagram() {
  return (
    <div className="cut" aria-hidden="true">
      <div className="cut-long">
        <span /><span /><span />
      </div>
      <div className="cut-arrow">↓</div>
      <div className="cut-clips">
        {['Long story,', 'cut', 'short.'].map((caption, index) => (
          <div className="cut-clip" key={caption} style={{ animationDelay: `${index * 0.12}s` }}>
            <b>{caption}</b>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Home() {
  const { user } = useAuth()
  const cta = user
    ? <Link to="/app" className="btn primary big">Open the studio</Link>
    : <Link to="/signup" className="btn primary big">Create your account</Link>

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">Qissa · <span lang="ar" dir="rtl">قصة</span> · “story”</p>
          <h1>Long story,<br /><em>cut short.</em></h1>
          <p className="lead">
            Upload one long video. Qissa cuts it into captioned, vertical YouTube Shorts and schedules them on your channel.
          </p>
          <div className="row wrap">
            {cta}
            {!user && <Link to="/login" className="btn ghost big">Log in</Link>}
          </div>
        </div>
        <CutDiagram />
      </section>

      <section className="home-section">
        <h2>How it works</h2>
        <ol className="how">
          {STEPS.map(([title, text], index) => (
            <li key={title}>
              <span className="how-number">{index + 1}</span>
              <strong>{title}</strong>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="home-section">
        <h2>What you control</h2>
        <ul className="features">
          {FEATURES.map(([title, text]) => (
            <li key={title}>
              <strong>{title}</strong>
              <p>{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="home-section closing">
        <h2>One video in. A week of Shorts out.</h2>
        <p className="lead">You bring the story and your YouTube channel. Qissa does the cutting.</p>
        {cta}
      </section>
    </main>
  )
}
