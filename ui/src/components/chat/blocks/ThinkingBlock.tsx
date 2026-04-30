import { useState } from 'react'

interface Props {
  content: string
}

export default function ThinkingBlock({ content }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-md border border-accent/20 overflow-hidden mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 bg-accent/[0.06] text-xs font-medium text-text-secondary hover:bg-accent/10 transition-colors"
      >
        <span className="text-text-tertiary">Thoughts</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <div className="px-3 py-2 bg-black/25 border-t border-accent/10 text-xs text-text-secondary font-mono whitespace-pre-wrap max-h-[400px] overflow-y-auto leading-relaxed">
          {content}
        </div>
      )}
    </div>
  )
}
