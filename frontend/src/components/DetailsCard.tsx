import type { UploadOptions } from '../api'
import { Card, ChipInput, Field, Toggle } from './ui'

const TITLE_LIMIT = 100
const hashtag = (raw: string) => {
  const tag = raw.replace(/[\s,#]+/g, '')
  return tag ? `#${tag}` : ''
}

/** Mirrors the backend's title rule: hashtags are added while they fit in 100 characters. */
function previewTitle(upload: UploadOptions) {
  let title = upload.title.trim()
  if (upload.number_clips) title = title ? `${title} - Part 1` : 'Part 1'
  if (upload.hashtags_in_title) {
    for (const tag of upload.hashtags) {
      const candidate = `${title} ${tag}`.trim()
      if (candidate.length > TITLE_LIMIT) break
      title = candidate
    }
  }
  return title.slice(0, TITLE_LIMIT) || 'Untitled Clip'
}

export function DetailsCard({ upload, onChange }: {
  upload: UploadOptions
  onChange: (patch: Partial<UploadOptions>) => void
}) {
  const title = previewTitle(upload)

  return (
    <Card step={2} title="Title & hashtags">
      <div className="stack">
        <Field label="Title">
          <input dir="auto" maxLength={TITLE_LIMIT} value={upload.title} placeholder="What is this video about?" onChange={(e) => onChange({ title: e.target.value })} />
        </Field>
        <Field label="Hashtags" hint="Press Enter or space to add">
          <ChipInput values={upload.hashtags} onChange={(hashtags) => onChange({ hashtags })} format={hashtag} placeholder="#shorts" />
        </Field>
        <Field label="Description (optional)" hint="Your hashtags and #Shorts are added at the end automatically">
          <textarea dir="auto" rows={2} value={upload.description} onChange={(e) => onChange({ description: e.target.value })} />
        </Field>
        <div className="row wrap">
          <Toggle checked={upload.hashtags_in_title} onChange={(hashtags_in_title) => onChange({ hashtags_in_title })} label="Put hashtags in the title" />
          <Toggle checked={upload.number_clips} onChange={(number_clips) => onChange({ number_clips })} label="Number the clips (Part 1, Part 2…)" />
        </div>
        <div className="title-preview">
          <span className="hint">Title on YouTube · {title.length}/{TITLE_LIMIT}</span>
          <strong dir="auto">{title}</strong>
        </div>
      </div>
    </Card>
  )
}
