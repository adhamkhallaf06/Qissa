import { useState, type KeyboardEvent, type ReactNode } from 'react'

export function Card({ step, title, aside, children }: {
  step?: number
  title: string
  aside?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="card">
      <header className="card-head">
        <h2>{step !== undefined && <span className="step">{step}</span>}{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="hint">{hint}</span>}
    </label>
  )
}

export function Toggle({ checked, onChange, label }: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
}) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" aria-hidden="true" />
      <span>{label}</span>
    </label>
  )
}

/** Free-text list editor: type, press Enter / comma / space to add a chip. */
export function ChipInput({ values, onChange, placeholder, format, type = 'text' }: {
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  format?: (raw: string) => string
  type?: 'text' | 'time'
}) {
  const [draft, setDraft] = useState('')

  const add = () => {
    const value = format ? format(draft) : draft.trim()
    if (value && !values.includes(value)) onChange([...values, value])
    setDraft('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || (type === 'text' && (e.key === ',' || e.key === ' '))) {
      e.preventDefault()
      add()
    } else if (e.key === 'Backspace' && !draft && values.length) {
      onChange(values.slice(0, -1))
    }
  }

  return (
    <div className="chips">
      {values.map((value) => (
        <span className="chip" key={value}>
          <span dir="auto">{value}</span>
          <button type="button" aria-label={`Remove ${value}`} onClick={() => onChange(values.filter((v) => v !== value))}>×</button>
        </span>
      ))}
      <input
        type={type}
        value={draft}
        placeholder={placeholder}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={add}
      />
    </div>
  )
}
