import { useState } from 'react'
import type { ServiceStatus, ServiceGroupId } from '../../types'
import { useServiceStore } from '../../stores/serviceStore'
import LogsModal from './LogsModal'

const GROUP_LABELS: Record<ServiceGroupId, string> = {
  inference: 'Inference',
  core: 'Core',
  memory: 'Memory',
  monitoring: 'Monitoring',
  media: 'Media',
  dev: 'Dev',
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'bg-success',
  unhealthy: 'bg-error',
  starting: 'bg-warning animate-pulse',
  stopped: 'bg-text-tertiary',
}

export default function ServiceGroupCard({ group, services }: { group: ServiceGroupId; services: ServiceStatus[] }) {
  const [expanded, setExpanded] = useState(false)
  const [logsFor, setLogsFor] = useState<{ id: string; name: string } | null>(null)
  const startService = useServiceStore((s) => s.startService)
  const stopService = useServiceStore((s) => s.stopService)
  const restartService = useServiceStore((s) => s.restartService)

  const healthy = services.filter((s) => s.health === 'healthy').length

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold">{GROUP_LABELS[group]}</span>
          <div className="flex gap-1">
            {services.map((s) => (
              <span key={s.id} className={`w-2 h-2 rounded-full ${HEALTH_COLORS[s.health]}`} title={`${s.name}: ${s.health}`} />
            ))}
          </div>
        </div>
        <span className="text-xs text-text-tertiary">{healthy}/{services.length}</span>
      </button>

      {expanded && (
        <div className="border-t border-border">
          {services.map((s) => (
            <div key={s.id} className="flex items-center justify-between px-4 py-2 border-b border-border last:border-b-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${HEALTH_COLORS[s.health]}`} />
                <span className="text-sm">{s.name}</span>
                <span className="text-xs text-text-tertiary">{s.health}</span>
                {s.accelerator === 'gpu' && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-400 font-medium">GPU</span>
                )}
                {s.accelerator === 'cpu' && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-500/20 text-zinc-400 font-medium">CPU</span>
                )}
                {s.ports?.map((p) => (
                  <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-black/30 text-text-tertiary font-mono">:{p}</span>
                ))}
              </div>
              <div className="flex gap-1 flex-shrink-0">
                <button
                  onClick={() => setLogsFor({ id: s.id, name: s.name })}
                  title="View logs"
                  className="text-xs px-2 py-1 rounded bg-white/5 text-text-tertiary hover:text-text-primary hover:bg-white/10 transition-colors"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
                </button>
                {s.health === 'stopped' || s.health === 'unhealthy' ? (
                  <button
                    onClick={() => startService(s.id)}
                    className="text-xs px-2 py-1 rounded bg-success/10 text-success hover:bg-success/20 transition-colors"
                  >
                    Start
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => restartService(s.id)}
                      className="text-xs px-2 py-1 rounded bg-warning/10 text-warning hover:bg-warning/20 transition-colors"
                    >
                      Restart
                    </button>
                    <button
                      onClick={() => stopService(s.id)}
                      className="text-xs px-2 py-1 rounded bg-error/10 text-error hover:bg-error/20 transition-colors"
                    >
                      Stop
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {logsFor && (
        <LogsModal serviceId={logsFor.id} serviceName={logsFor.name} onClose={() => setLogsFor(null)} />
      )}
    </div>
  )
}
