import type { CSSProperties } from 'react'
import type { CaptionOptions } from '../api'

// The backend's subtitle canvas is 288 units tall; the preview scales to it.
const CANVAS_HEIGHT = 288
const PREVIEW_HEIGHT = 400
const SAMPLE = 'This is how your captions look'

/** Approximate an outline with stacked text shadows. */
function outline(width: number, color: string) {
  if (width <= 0) return []
  const shadows: string[] = []
  for (let angle = 0; angle < 360; angle += 30) {
    const x = Math.cos((angle * Math.PI) / 180) * width
    const y = Math.sin((angle * Math.PI) / 180) * width
    shadows.push(`${x.toFixed(2)}px ${y.toFixed(2)}px 0 ${color}`)
  }
  return shadows
}

export function CaptionPreview({ captions, vertical }: { captions: CaptionOptions; vertical: boolean }) {
  const scale = PREVIEW_HEIGHT / CANVAS_HEIGHT
  // The renderer sizes fonts by line height, so glyphs come out smaller than a CSS font-size
  const fontScale = scale * 0.7
  const words = SAMPLE.split(' ')
  const text = (captions.max_words ? words.slice(0, captions.max_words) : words).join(' ')

  const shadows = captions.background ? [] : outline(captions.outline_width * scale * 0.6, captions.outline_color)
  if (captions.shadow > 0) {
    const offset = captions.shadow * scale * 0.6
    shadows.push(`${offset}px ${offset}px 0 rgba(0,0,0,.8)`)
  }

  const style: CSSProperties = {
    fontFamily: `"${captions.font_name}", Arial, sans-serif`,
    fontSize: captions.font_size * fontScale,
    fontWeight: captions.bold ? 700 : 400,
    fontStyle: captions.italic ? 'italic' : 'normal',
    textTransform: captions.uppercase ? 'uppercase' : 'none',
    color: captions.colors[0],
    textShadow: shadows.join(', ') || 'none',
    background: captions.background ? captions.background_color : 'transparent',
    padding: captions.background ? `${2 * scale}px ${4 * scale}px` : 0,
  }

  const placement: CSSProperties =
    captions.position === 'top' ? { top: captions.margin_v * scale }
    : captions.position === 'bottom' ? { bottom: captions.margin_v * scale }
    : { top: '50%', transform: 'translateY(-50%)' }

  return (
    <div className="preview" style={{ height: PREVIEW_HEIGHT }}>
      <div className={`preview-video ${vertical ? '' : 'landscape'}`}>source video</div>
      {captions.enabled ? (
        <div className="preview-caption" style={placement}>
          <span style={style}>{text}</span>
        </div>
      ) : (
        <div className="preview-caption muted" style={{ bottom: 16 }}>Captions off</div>
      )}
    </div>
  )
}
