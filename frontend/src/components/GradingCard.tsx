import type { GradingOptions, GradingStatus } from '../api'
import { Card, Field, Toggle } from './ui'

export function GradingCard({ grading, status, uploading, onChange }: {
  grading: GradingOptions
  status: GradingStatus | null
  uploading: boolean
  onChange: (grading: GradingOptions) => void
}) {
  const available = status?.available ?? false

  return (
    <Card
      step={4}
      title="Pick the best clips"
      aside={available && (
        <Toggle checked={grading.enabled} onChange={(enabled) => onChange({ ...grading, enabled })} label="Grade with AI" />
      )}
    >
      {!available ? (
        <p className="hint">
          To grade clips, put an Anthropic API key in <code>backend/secrets/anthropic_api_key</code> (or
          set <code>ANTHROPIC_API_KEY</code>) and restart the backend. Until then every clip is uploaded.
        </p>
      ) : !grading.enabled ? (
        <p className="hint">Every clip that passes the silence check will be uploaded.</p>
      ) : (
        <div className="stack">
          <p className="hint">
            Claude watches each clip (transcript plus a few frames) and scores it 1–10 on its hook, whether it
            stands on its own, and its payoff. {uploading
              ? 'Only the best ones are uploaded, the best going into the first time slot.'
              : 'Uploading is off, so you just get the scores.'}
          </p>
          <Field label="How many to upload" hint="The rest stay here with their scores.">
            <input
              type="number"
              min={1}
              max={100}
              value={grading.top_n}
              disabled={!uploading}
              onChange={(e) => onChange({ ...grading, top_n: Math.max(1, Math.min(100, Number(e.target.value) || 1)) })}
            />
          </Field>
        </div>
      )}
    </Card>
  )
}
