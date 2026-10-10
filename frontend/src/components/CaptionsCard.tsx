import type { CaptionOptions, PipelineOptions } from '../api'
import { CaptionPreview } from './CaptionPreview'
import { Card, Field, Toggle } from './ui'

const LANGUAGES: [string, string][] = [
  ['', 'Auto-detect'], ['ar', 'Arabic'], ['en', 'English'], ['fr', 'French'], ['es', 'Spanish'],
  ['de', 'German'], ['tr', 'Turkish'], ['ur', 'Urdu'], ['hi', 'Hindi'], ['id', 'Indonesian'],
  ['pt', 'Portuguese'], ['ru', 'Russian'], ['it', 'Italian'], ['ja', 'Japanese'], ['ko', 'Korean'], ['zh', 'Chinese'],
]
const FONTS = ['Arial Unicode MS', 'Arial', 'Helvetica', 'Impact', 'Verdana', 'Georgia', 'Courier New', 'Geeza Pro', 'Damascus']
const MODELS: [CaptionOptions['model'], string][] = [
  ['tiny', 'Tiny — fastest'], ['base', 'Base'], ['small', 'Small'], ['medium', 'Medium'], ['large', 'Large — most accurate'],
]

export function CaptionsCard({ options, onChange }: {
  options: PipelineOptions
  onChange: (options: PipelineOptions) => void
}) {
  const captions = options.captions
  const set = (patch: Partial<CaptionOptions>) => onChange({ ...options, captions: { ...captions, ...patch } })
  const setColor = (index: number, color: string) =>
    set({ colors: captions.colors.map((c, i) => (i === index ? color : c)) })

  return (
    <Card
      step={3}
      title="Captions & processing"
      aside={<Toggle checked={captions.enabled} onChange={(enabled) => set({ enabled })} label="Burn in captions" />}
    >
      <div className="captions-layout">
        <div className="stack">
          <fieldset disabled={!captions.enabled} className="stack">
            <div className="grid-2">
              <Field label="Spoken language">
                <select value={captions.language ?? ''} onChange={(e) => set({ language: e.target.value || null })}>
                  {LANGUAGES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
                </select>
              </Field>
              <Field label="Accuracy">
                <select value={captions.model} onChange={(e) => set({ model: e.target.value as CaptionOptions['model'] })}>
                  {MODELS.map(([value, name]) => <option key={value} value={value}>{name}</option>)}
                </select>
              </Field>
            </div>

            <div className="grid-2">
              <Field label="Font" hint="Must be installed on the machine running the backend">
                <input list="fonts" value={captions.font_name} onChange={(e) => set({ font_name: e.target.value })} />
                <datalist id="fonts">{FONTS.map((font) => <option key={font} value={font} />)}</datalist>
              </Field>
              <Field label={`Size — ${captions.font_size}`}>
                <input type="range" min={6} max={40} value={captions.font_size} onChange={(e) => set({ font_size: Number(e.target.value) })} />
              </Field>
            </div>

            <div className="row wrap">
              <Toggle checked={captions.bold} onChange={(bold) => set({ bold })} label="Bold" />
              <Toggle checked={captions.italic} onChange={(italic) => set({ italic })} label="Italic" />
              <Toggle checked={captions.uppercase} onChange={(uppercase) => set({ uppercase })} label="UPPERCASE" />
            </div>

            <Field label="Text colors" hint="Captions cycle through these, one color per line">
              <div className="row wrap">
                {captions.colors.map((color, index) => (
                  <span className="swatch" key={index}>
                    <input type="color" value={color} aria-label={`Text color ${index + 1}`} onChange={(e) => setColor(index, e.target.value)} />
                    {captions.colors.length > 1 && (
                      <button type="button" aria-label={`Remove color ${index + 1}`} onClick={() => set({ colors: captions.colors.filter((_, i) => i !== index) })}>×</button>
                    )}
                  </span>
                ))}
                {captions.colors.length < 6 && (
                  <button type="button" className="btn small" onClick={() => set({ colors: [...captions.colors, '#ffffff'] })}>+ Add</button>
                )}
              </div>
            </Field>

            <div className="grid-2">
              <Field label={`Outline — ${captions.outline_width}`}>
                <div className="row">
                  <input type="color" value={captions.outline_color} aria-label="Outline color" disabled={captions.background} onChange={(e) => set({ outline_color: e.target.value })} />
                  <input type="range" min={0} max={6} step={0.5} value={captions.outline_width} onChange={(e) => set({ outline_width: Number(e.target.value) })} />
                </div>
              </Field>
              <Field label={`Shadow — ${captions.shadow}`}>
                <input type="range" min={0} max={6} step={0.5} value={captions.shadow} onChange={(e) => set({ shadow: Number(e.target.value) })} />
              </Field>
            </div>

            <div className="row wrap">
              <Toggle checked={captions.background} onChange={(background) => set({ background })} label="Solid box behind text" />
              {captions.background && (
                <input type="color" value={captions.background_color} aria-label="Box color" onChange={(e) => set({ background_color: e.target.value })} />
              )}
            </div>

            <div className="grid-2">
              <Field label="Position">
                <div className="segmented">
                  {(['top', 'middle', 'bottom'] as const).map((position) => (
                    <button type="button" key={position} className={captions.position === position ? 'active' : ''} onClick={() => set({ position })}>
                      {position}
                    </button>
                  ))}
                </div>
              </Field>
              <Field label={`Distance from edge — ${captions.margin_v}`}>
                <input type="range" min={0} max={130} disabled={captions.position === 'middle'} value={captions.margin_v} onChange={(e) => set({ margin_v: Number(e.target.value) })} />
              </Field>
            </div>

            <Field label="Words on screen at once" hint="Fewer words gives the fast, punchy Shorts style">
              <select value={captions.max_words ?? ''} onChange={(e) => set({ max_words: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Full sentence</option>
                {[1, 2, 3, 4, 5, 6, 8].map((n) => <option key={n} value={n}>{n} {n === 1 ? 'word' : 'words'}</option>)}
              </select>
            </Field>
          </fieldset>

          <hr />

          <div className="grid-2">
            <Field label={`Clip length — ${options.clip_seconds}s`}>
              <input type="range" min={15} max={180} step={5} value={options.clip_seconds} onChange={(e) => onChange({ ...options, clip_seconds: Number(e.target.value) })} />
            </Field>
            <Field label="Max silence per clip (seconds)">
              <input type="number" min={0} step={0.5} disabled={!options.remove_silent} value={options.max_silence_seconds} onChange={(e) => onChange({ ...options, max_silence_seconds: Number(e.target.value) })} />
            </Field>
          </div>
          <div className="row wrap">
            <Toggle checked={options.vertical} onChange={(vertical) => onChange({ ...options, vertical })} label="Convert to vertical 9:16" />
            <Toggle checked={options.remove_silent} onChange={(remove_silent) => onChange({ ...options, remove_silent })} label="Drop mostly-silent clips" />
          </div>
        </div>

        <CaptionPreview captions={captions} vertical={options.vertical} />
      </div>
    </Card>
  )
}
