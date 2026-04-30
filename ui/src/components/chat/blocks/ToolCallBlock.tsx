import { useState } from 'react'

interface Props {
  tool: string
  args: Record<string, unknown>
}

export default function ToolCallBlock({ tool, args }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-md border-l-2 border-l-info bg-surface overflow-hidden mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-hover transition-colors"
      >
        <span className="font-mono font-semibold text-text-secondary">{tool}</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
    </div>
  )
}
