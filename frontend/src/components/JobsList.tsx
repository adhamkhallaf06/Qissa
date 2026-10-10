import { api, type Job, type JobStatus } from '../api'

const LABELS: Record<JobStatus, string> = {
  queued: 'Waiting',
  splitting: 'Cutting into clips',
  processing: 'Adding captions',
  cleaning: 'Checking audio',
  uploading: 'Uploading to YouTube',
  done: 'Done',
  failed: 'Failed',
}
const STEPS: JobStatus[] = ['splitting', 'processing', 'cleaning', 'uploading']

const isActive = (status: JobStatus) => status !== 'done' && status !== 'failed'
const when = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function Progress({ job }: { job: Job }) {
  const steps = STEPS.filter((step) =>
    (step !== 'cleaning' || job.options.remove_silent) && (step !== 'uploading' || job.options.upload.enabled))
  const current = steps.indexOf(job.status)
  return (
    <div className="progress" aria-label={LABELS[job.status]}>
      {steps.map((step, index) => (
        <span key={step} className={index < current ? 'past' : index === current ? 'current' : ''} />
      ))}
    </div>
  )
}

export function JobsList({ jobs, onDelete }: { jobs: Job[]; onDelete: (job: Job) => void }) {
  if (!jobs.length) {
    return <p className="hint empty">Nothing yet. Videos you start will show up here with their clips.</p>
  }

  return (
    <ul className="jobs">
      {jobs.map((job) => (
        <li key={job.id} className="job">
          <div className="job-head">
            <div>
              <strong dir="auto">{job.filename}</strong>
              <span className="hint">{when(job.created_at)}</span>
            </div>
            <span className={`pill ${job.status === 'done' ? 'ok' : job.status === 'failed' ? 'bad' : 'busy'}`}>
              {LABELS[job.status]}
            </span>
          </div>

          {isActive(job.status) && <Progress job={job} />}
          {job.error && <p className="error">{job.error}</p>}

          {job.uploads.length > 0 && (
            <ul className="uploads">
              {job.uploads.map((video) => (
                <li key={video.video_id}>
                  <a href={`https://youtu.be/${video.video_id}`} target="_blank" rel="noreferrer" dir="auto">{video.title}</a>
                  <span className="hint">{video.publish_at ? `Goes public ${when(video.publish_at)}` : 'Uploaded'}</span>
                </li>
              ))}
            </ul>
          )}

          {job.clips.length > 0 && (
            <div className="clips">
              {job.clips.map((clip) => (
                <video key={clip} src={api.clipUrl(job.id, clip)} controls preload="metadata" title={clip} />
              ))}
            </div>
          )}
          {job.status === 'done' && !job.clips.length && !job.uploads.length && (
            <p className="hint">No clips were kept — they were all filtered out as silent.</p>
          )}

          <div className="job-foot">
            {job.log.length > 0 && (
              <details>
                <summary>Log</summary>
                <pre dir="auto">{job.log.join('\n')}</pre>
              </details>
            )}
            {!isActive(job.status) && (
              <button type="button" className="btn ghost small" onClick={() => onDelete(job)}>Delete</button>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}
