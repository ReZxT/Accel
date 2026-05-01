import { useState, useEffect, useRef } from 'react'
import { electronServices } from '../../api/electron'

interface Props {
  serviceId: string
  serviceName: string
  onClose: () => void
}

export default function LogsModal({ serviceId, serviceName, onClose }: Props) {
  const [logs, setLogs] = useState<string>('Loading...')
  const [loading, setLoading] = useState(true)
  const preRef = useRef<HTMLPreElement>(null)

  const fetchLogs = async () => {
    setLoading(true)
    const result = await electronServices.logs(serviceId)
    setLogs(result)
    setLoading(false)
    setTimeout(() => {
      if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight
    }, 0)
  }

  useEffect(() => { fetchLogs() }, [serviceId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-bg-secondary border border-border rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col" style={{ minWidth: 0 }}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
          <span className="text-sm font-semibold font-mono">{serviceName} — logs</span>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="text-xs px-2 py-1 rounded border border-border text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors disabled:opacity-50"
            >
              Refresh
            </button>
            <button onClick={onClose} className="text-text-tertiary hover:text-text-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>
        <pre
          ref={preRef}
          className="flex-1 overflow-y-auto p-4 text-xs font-mono text-text-secondary leading-relaxed whitespace-pre-wrap break-all"
        >
          {loading ? 'Loading...' : logs}
        </pre>
      </div>
    </div>
  )
}
