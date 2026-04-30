import { useState } from 'react'
import { useUIStore } from '../../../stores/uiStore'

interface Props {
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export default function ToolResultBlock({ tool, output, image, mime_type }: Props) {
  const [open, setOpen] = useState(false)
  const openPanel = useUIStore((s) => s.openPanel)

  if (image) {
    const src = `data:${mime_type || 'image/png'};base64,${image}`
    return (
      <div className="rounded-md border-l-2 border-l-success bg-surface overflow-hidden mb-1">
        <div className="px-3 py-1.5 text-xs">
          <span className="font-mono font-semibold text-text-secondary">{tool}</span>
          <span className="text-text-tertiary ml-2">screenshot</span>
        </div>
        <img
          src={src}
          alt="Screenshot"
          className="max-w-full rounded-sm mx-3 mb-2 border border-border cursor-pointer hover:opacity-90 transition-opacity"
          onClick={() => openPanel('image', src)}
        />
      </div>
    )
  }

  const truncated = output.length > 2000 ? output.slice(0, 2000) + '\n... (truncated)' : output

  return (
    <div className="rounded-md border-l-2 border-l-success bg-surface overflow-hidden mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-hover transition-colors"
      >
        <span className="font-mono font-semibold text-text-secondary">{tool}</span>
        <span className="text-text-tertiary">result</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
          {truncated}
        </pre>
      )}
    </div>
  )
}
