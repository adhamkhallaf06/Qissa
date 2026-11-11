import { useCallback, useEffect, useState } from 'react'
import { api, type GradingStatus, type History, type HistoryKind, type Job, type PipelineOptions, type UploadOptions, type YouTubeStatus } from '../api'
import { CaptionsCard } from '../components/CaptionsCard'
import { DetailsCard } from '../components/DetailsCard'
import { GradingCard } from '../components/GradingCard'
import { JobsList } from '../components/JobsList'
import { ScheduleCard } from '../components/ScheduleCard'
import { Card } from '../components/ui'
import { VideoDrop } from '../components/VideoDrop'
import { YouTubeCard } from '../components/YouTubeCard'

const JOBS_POLL_MS = 2500
const YOUTUBE_LINK = /^https?:\/\/(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//i

type Source = 'link' | 'file'

export function Studio() {
  const [options, setOptions] = useState<PipelineOptions | null>(null)
  const [source, setSource] = useState<Source>('link')
  const [file, setFile] = useState<File | null>(null)
  const [link, setLink] = useState('')
  const [youtube, setYoutube] = useState<YouTubeStatus | null>(null)
  const [grading, setGrading] = useState<GradingStatus | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [history, setHistory] = useState<History | null>(null)
  const [loadError, setLoadError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [progress, setProgress] = useState<number | null>(null)

  const refreshJobs = useCallback(() => api.jobs().then(setJobs).catch(() => {}), [])
  const refreshHistory = useCallback(() => api.history().then(setHistory).catch(() => {}), [])

  const load = useCallback(async () => {
    try {
      const [defaults, status, gradingStatus] = await Promise.all([api.defaults(), api.youtubeStatus(), api.gradingStatus()])
      // The form starts empty; publish times are in the viewer's own timezone unless they pick another
      defaults.upload.schedule.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || defaults.upload.schedule.timezone
      setOptions((current) => current ?? defaults)
      setYoutube(status)
      setGrading(gradingStatus)
      setLoadError('')
    } catch (e) {
      setLoadError((e as Error).message)
    }
  }, [])

  useEffect(() => {
    load()
    refreshJobs()
    refreshHistory()
    const timer = setInterval(refreshJobs, JOBS_POLL_MS)
    return () => clearInterval(timer)
  }, [load, refreshJobs, refreshHistory])

  if (!options) {
    return (
      <main className="page center">
        {loadError ? (
          <div className="card stack">
            <p className="error" role="alert">{loadError}</p>
            <p className="hint">Start it from <code>backend/</code> with <code>uvicorn app.api.app:app --port 8000</code></p>
            <button type="button" className="btn primary" onClick={load}>Try again</button>
          </div>
        ) : <p className="hint">Loading…</p>}
      </main>
    )
  }

  const upload = options.upload
  const setUpload = (patch: Partial<UploadOptions>) => setOptions({ ...options, upload: { ...upload, ...patch } })

  const needsYouTube = upload.enabled && !youtube?.connected
  const trimmedLink = link.trim()
  const blocker = source === 'file' && !file ? 'Choose a video first'
    : source === 'link' && !trimmedLink ? 'Paste a YouTube link first'
    : source === 'link' && !YOUTUBE_LINK.test(trimmedLink) ? 'That doesn’t look like a YouTube link'
    : upload.enabled && upload.schedule.enabled && !upload.schedule.time_slots.length ? 'Add a publish time in step 5, or choose Publish right away'
    : needsYouTube ? 'Connect YouTube, or turn off uploading in step 5'
    : ''

  const submit = async () => {
    if (blocker) return
    setSubmitError('')
    setProgress(0)
    try {
      if (source === 'link') {
        // The backend checks the link before answering, so this can take a few seconds
        setProgress(1)
        await api.createJobFromLink(trimmedLink, options)
        setLink('')
      } else if (file) {
        await api.createJob(file, options, setProgress)
        setFile(null)
      }
      await Promise.all([refreshJobs(), refreshHistory()])
      document.getElementById('jobs')?.scrollIntoView({ behavior: 'smooth' })
    } catch (e) {
      setSubmitError((e as Error).message)
    } finally {
      setProgress(null)
    }
  }

  const forget = <K extends HistoryKind>(kind: K, value: History[K][number]['value']) => {
    // Hide it right away; the server copy follows
    setHistory((h) => h && { ...h, [kind]: h[kind].filter((item) => item.value !== value) })
    api.forgetHistory(kind, value).catch(() => {}).finally(refreshHistory)
  }

  const retryUpload = async (job: Job) => {
    setSubmitError('')
    try {
      await api.retryUpload(job.id)
    } catch (e) {
      window.alert((e as Error).message)
    }
    refreshJobs()
  }

  const deleteJob = async (job: Job) => {
    if (!window.confirm(`Delete "${job.filename}" and its clips from this computer?`)) return
    await api.deleteJob(job.id).catch((e) => setSubmitError((e as Error).message))
    refreshJobs()
  }

  return (
    <main className="page">
      <header className="page-head">
        <h1>New Shorts</h1>
        <p className="hint">Turn one long video into captioned, scheduled YouTube Shorts.</p>
      </header>

      <Card step={1} title="Video">
        <div className="stack">
          <div className="segmented wide plain" role="tablist" aria-label="Video source">
            {(['link', 'file'] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={source === value}
                className={source === value ? 'active' : ''}
                onClick={() => setSource(value)}
              >
                {value === 'link' ? 'YouTube link' : 'Upload a file'}
              </button>
            ))}
          </div>
          {source === 'link' ? (
            <label className="field">
              <span className="field-label">Video link</span>
              <input
                type="url"
                inputMode="url"
                placeholder="https://www.youtube.com/watch?v=…"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
              />
              <span className="hint">Qissa downloads the video, cuts it into {options.clip_seconds}-second Shorts, and uploads them to your channel. Only use videos you have the rights to.</span>
            </label>
          ) : (
            <VideoDrop file={file} onChange={setFile} />
          )}
        </div>
      </Card>

      <DetailsCard upload={upload} onChange={setUpload} history={history} onForget={forget} />
      <CaptionsCard options={options} onChange={setOptions} history={history} onForget={forget} />
      <GradingCard
        grading={options.grading}
        status={grading}
        uploading={upload.enabled}
        onChange={(value) => setOptions({ ...options, grading: value })}
      />
      <ScheduleCard upload={upload} onChange={setUpload} history={history} onForget={forget} />
      {upload.enabled && <YouTubeCard status={youtube} onStatus={setYoutube} />}

      <div className="submit">
        {submitError && <p className="error" role="alert">{submitError}</p>}
        <button type="button" className="btn primary big" disabled={!!blocker || progress !== null} onClick={submit}>
          {progress === null ? 'Create Shorts'
            : progress < 1 ? `Uploading video… ${Math.round(progress * 100)}%`
            : source === 'link' ? 'Checking link…'
            : 'Starting…'}
        </button>
        {blocker && <span className="hint">{blocker}</span>}
      </div>

      <section id="jobs">
        <h2 className="section-title">Your videos</h2>
        <JobsList jobs={jobs} onDelete={deleteJob} onRetry={retryUpload} />
      </section>
    </main>
  )
}
