import { useMemo } from 'react'
import type { ScheduleOptions, UploadOptions } from '../api'
import { Card, ChipInput, Field, Toggle } from './ui'

function timezones(current: string) {
  let zones: string[] = []
  try {
    zones = Intl.supportedValuesOf('timeZone')
  } catch {
    // older browsers
  }
  return zones.includes(current) ? zones : [current, ...zones]
}

export function ScheduleCard({ upload, onChange }: {
  upload: UploadOptions
  onChange: (patch: Partial<UploadOptions>) => void
}) {
  const schedule = upload.schedule
  const set = (patch: Partial<ScheduleOptions>) => onChange({ schedule: { ...schedule, ...patch } })
  const zones = useMemo(() => timezones(schedule.timezone), [schedule.timezone])
  const local = Intl.DateTimeFormat().resolvedOptions().timeZone

  return (
    <Card
      step={4}
      title="When to publish"
      aside={<Toggle checked={upload.enabled} onChange={(enabled) => onChange({ enabled })} label="Upload to YouTube" />}
    >
      {!upload.enabled ? (
        <p className="hint">Clips will be processed and kept here for you to preview. Nothing is sent to YouTube.</p>
      ) : (
        <div className="stack">
          <div className="segmented wide">
            <button type="button" className={schedule.enabled ? 'active' : ''} onClick={() => set({ enabled: true })}>Schedule</button>
            <button type="button" className={!schedule.enabled ? 'active' : ''} onClick={() => set({ enabled: false })}>Publish right away</button>
          </div>

          {schedule.enabled ? (
            <>
              <Field label="Publish times" hint="One clip goes out at each time. Extra clips continue on the following days.">
                <ChipInput
                  type="time"
                  values={schedule.time_slots}
                  onChange={(time_slots) => time_slots.length && set({ time_slots: [...time_slots].sort() })}
                />
              </Field>
              <div className="grid-2">
                <Field label="Start date" hint="Empty = tomorrow">
                  <input type="date" value={schedule.start_date ?? ''} onChange={(e) => set({ start_date: e.target.value || null })} />
                </Field>
                <Field label="Timezone">
                  <select value={schedule.timezone} onChange={(e) => set({ timezone: e.target.value })}>
                    {zones.map((zone) => <option key={zone} value={zone}>{zone}</option>)}
                  </select>
                </Field>
              </div>
              {local !== schedule.timezone && (
                <button type="button" className="btn small" onClick={() => set({ timezone: local })}>Use my timezone ({local})</button>
              )}
            </>
          ) : (
            <Field label="Visibility">
              <select value={upload.privacy} onChange={(e) => onChange({ privacy: e.target.value as UploadOptions['privacy'] })}>
                <option value="private">Private</option>
                <option value="unlisted">Unlisted</option>
                <option value="public">Public</option>
              </select>
            </Field>
          )}

          <Toggle checked={!upload.delete_after_upload} onChange={(keep) => onChange({ delete_after_upload: !keep })} label="Keep the clips here after uploading" />
        </div>
      )}
    </Card>
  )
}
