export interface CaptionOptions {
  enabled: boolean
  language: string | null
  model: 'tiny' | 'base' | 'small' | 'medium' | 'large'
  max_words: number | null
  font_name: string
  font_size: number
  bold: boolean
  italic: boolean
  uppercase: boolean
  colors: string[]
  outline_color: string
  outline_width: number
  shadow: number
  background: boolean
  background_color: string
  position: 'top' | 'middle' | 'bottom'
  margin_v: number
}

export interface ScheduleOptions {
  enabled: boolean
  timezone: string
  start_date: string | null
  time_slots: string[]
}

export interface UploadOptions {
  enabled: boolean
  title: string
  description: string
  hashtags: string[]
  hashtags_in_title: boolean
  number_clips: boolean
  category_id: string
  privacy: 'private' | 'unlisted' | 'public'
  schedule: ScheduleOptions
  delete_after_upload: boolean
}

export interface PipelineOptions {
  clip_seconds: number
  vertical: boolean
  remove_silent: boolean
  max_silence_seconds: number
  captions: CaptionOptions
  upload: UploadOptions
}

export interface YouTubeStatus {
  has_client_secret: boolean
  connected: boolean
  redirect_uri: string
}

export type JobStatus =
  | 'queued' | 'splitting' | 'processing' | 'cleaning' | 'uploading' | 'done' | 'failed'

export interface UploadedVideo {
  file: string
  video_id: string
  title: string
  publish_at: string | null
}

export interface Job {
  id: string
  filename: string
  status: JobStatus
  error: string | null
  created_at: string
  options: PipelineOptions
  uploads: UploadedVideo[]
  log: string[]
  clips: string[]
}

async function errorMessage(response: Response) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg as string
  } catch {
    // not JSON
  }
  return `Request failed (${response.status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new Error('Cannot reach the backend. Is it running on port 8000?')
  }
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.status === 204 ? (undefined as T) : response.json()
}

export const api = {
  defaults: () => request<PipelineOptions>('/api/options/defaults'),
  jobs: () => request<Job[]>('/api/jobs'),
  deleteJob: (id: string) => request<void>(`/api/jobs/${id}`, { method: 'DELETE' }),
  clipUrl: (jobId: string, name: string) => `/api/jobs/${jobId}/clips/${encodeURIComponent(name)}`,

  youtubeStatus: () => request<YouTubeStatus>('/api/youtube/status'),
  youtubeConnect: () => request<{ auth_url: string }>('/api/youtube/connect'),
  youtubeDisconnect: () => request<YouTubeStatus>('/api/youtube/connection', { method: 'DELETE' }),
  uploadClientSecret: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<YouTubeStatus>('/api/youtube/client-secret', { method: 'POST', body })
  },

  /** Upload a video and start a job. XHR instead of fetch so we get upload progress. */
  createJob: (file: File, options: PipelineOptions, onProgress: (fraction: number) => void) =>
    new Promise<Job>((resolve, reject) => {
      const body = new FormData()
      body.append('file', file)
      body.append('options', JSON.stringify(options))

      const xhr = new XMLHttpRequest()
      xhr.open('POST', '/api/jobs')
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total)
      xhr.onerror = () => reject(new Error('Cannot reach the backend. Is it running on port 8000?'))
      xhr.onload = () => {
        let parsed: unknown = null
        try {
          parsed = JSON.parse(xhr.responseText)
        } catch {
          // not JSON
        }
        if (xhr.status >= 200 && xhr.status < 300) return resolve(parsed as Job)
        const detail = (parsed as { detail?: unknown } | null)?.detail
        reject(new Error(typeof detail === 'string' ? detail : `Upload failed (${xhr.status})`))
      }
      xhr.send(body)
    }),
}
