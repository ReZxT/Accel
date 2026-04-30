import { resolveApproval } from '../../../api/tools'
import { useChatStore } from '../../../stores/chatStore'
import type { StreamingApproval } from '../../../types'

interface Props {
  approval: StreamingApproval
}

export default function ApprovalBlock({ approval }: Props) {
  const resolve = useChatStore((s) => s.resolveApproval)

  const handleResolve = (approved: boolean) => {
    resolve(approval.request_id, approved)
    resolveApproval(approval.request_id, approved).catch(() => {})
  }

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
      </div>
      <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
        {JSON.stringify(approval.args, null, 2)}
      </pre>
      <div className="flex gap-2 px-3 py-2 border-t border-border">
        <button
          onClick={() => handleResolve(true)}
          className="px-3 py-1 rounded text-xs font-semibold bg-success/20 text-success hover:bg-success/30 transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => handleResolve(false)}
          className="px-3 py-1 rounded text-xs font-semibold bg-error/20 text-error hover:bg-error/30 transition-colors"
        >
          Deny
        </button>
      </div>
    </div>
  )
}
