import { useRef, useState } from 'react'

const formatSize = (bytes: number) =>
  bytes > 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${(bytes / 1e6).toFixed(1)} MB`

export function VideoDrop({ file, onChange }: { file: File | null; onChange: (file: File | null) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  return (
    <div
      className={`drop ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        const dropped = e.dataTransfer.files[0]
        if (dropped) onChange(dropped)
      }}
    >
      <input
        ref={input}
        type="file"
        accept="video/*,.mkv,.flv,.avi"
        hidden
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <>
          <div className="drop-file">
            <strong dir="auto">{file.name}</strong>
            <span className="hint">{formatSize(file.size)}</span>
          </div>
          <div className="row">
            <button type="button" className="btn" onClick={() => input.current?.click()}>Replace</button>
            <button type="button" className="btn ghost" onClick={() => { onChange(null); if (input.current) input.current.value = '' }}>Remove</button>
          </div>
        </>
      ) : (
        <>
          <p><strong>Drop a video here</strong></p>
          <p className="hint">mp4, mov, mkv, avi, webm — it will be cut into Shorts</p>
          <button type="button" className="btn" onClick={() => input.current?.click()}>Choose file</button>
        </>
      )}
    </div>
  )
}
