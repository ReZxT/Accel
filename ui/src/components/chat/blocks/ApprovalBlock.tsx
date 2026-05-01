import { useState, useEffect } from 'react'
import { resolveApproval } from '../../../api/tools'
import { useChatStore } from '../../../stores/chatStore'
import type { StreamingApproval } from '../../../types'

interface Props {
  approval: StreamingApproval
}

export default function ApprovalBlock({ approval }: Props) {
  const resolve = useChatStore((s) => s.resolveApproval)
  const [selected, setSelected] = useState<'approve' | 'deny'>('approve')

  const handleResolve = (approved: boolean) => {
    resolve(approval.request_id, approved)
    resolveApproval(approval.request_id, approved).catch(() => {})
  }

  // Global keydown capture so keys work regardless of where focus is
  useEffect(() => {
    if (approval.resolved) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Tab') {
        e.preventDefault()
        setSelected((s) => (s === 'approve' ? 'deny' : 'approve'))
      }
      if (e.key === 'Enter') {
        e.preventDefault()
        e.stopPropagation()
        handleResolve(selected === 'approve')
      }
    }
    window.addEventListener('keydown', handler, true)
    return () => window.removeEventListener('keydown', handler, true)
  }, [approval.resolved, selected])

  if (approval.resolved) {
    return (
      <div
        className={`rounded-md border-l-2 px-3 py-1.5 text-xs font-semibold mb-1 ${
          approval.approved
            ? 'border-l-success bg-success/[0.06] text-success'
            : 'border-l-error bg-error/[0.06] text-error'
        }`}
      >
        {approval.approved ? 'Approved' : 'Denied'}: {approval.tool}
      </div>
    )
  }

  return (
    <div className="rounded-md border-l-2 border-l-warning bg-warning/[0.06] overflow-hidden mb-1">
      <div className="px-3 py-1.5 text-xs">
        <span className="font-mono font-semibold text-text-secondary">{approval.tool}</span>
        <span className="text-warning ml-2">requires approval</span>
        <span className="text-text-tertiary ml-2 text-[10px]">← → to switch · Enter to confirm</span>
      </div>
      <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
        {JSON.stringify(approval.args, null, 2)}
      </pre>
      <div className="flex gap-2 px-3 py-2 border-t border-border">
        <button
          onClick={() => handleResolve(true)}
          className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
            selected === 'approve'
              ? 'bg-success/30 text-success ring-1 ring-success/60'
              : 'bg-success/10 text-success hover:bg-success/20'
          }`}
        >
          Approve
        </button>
        <button
          onClick={() => handleResolve(false)}
          className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
            selected === 'deny'
              ? 'bg-error/30 text-error ring-1 ring-error/60'
              : 'bg-error/10 text-error hover:bg-error/20'
          }`}
        >
          Deny
        </button>
      </div>
    </div>
  )
}
