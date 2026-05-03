import { useEffect, useState } from 'react'
import { fetchMetrics, type MetricSeries } from '../../api/metrics'

const COLORS: Record<string, string> = {
  CPU: '#8b5cf6',
  RAM: '#3b82f6',
  GPU: '#f59e0b',
  VRAM: '#ef4444',
  'GPU Temp': '#f97316',
  'GPU Power': '#eab308',
  'Disk /': '#6366f1',
}

function Sparkline({ series }: { series: MetricSeries }) {
  const { points, max, current, label, unit } = series
  if (points.length < 2) return null

  const w = 200
  const h = 48
  const padTop = 2
  const padBot = 2
  const usable = h - padTop - padBot

  const color = COLORS[label] ?? '#8b5cf6'

  const xs = points.map((_, i) => (i / (points.length - 1)) * w)
  const ys = points.map((p) => padTop + usable - (p.v / max) * usable)

  const linePoints = xs.map((x, i) => `${x},${ys[i]}`).join(' ')
  const areaPoints = `0,${h} ${linePoints} ${w},${h}`

  const pct = max === 100

  return (
    <div className="flex items-center gap-3">
      <div className="w-20 flex-shrink-0">
        <div className="text-[11px] text-text-tertiary leading-none mb-1">{label}</div>
        <div className="text-sm font-mono font-semibold leading-none" style={{ color }}>
          {current}{pct ? '%' : ` ${unit}`}
        </div>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="flex-1 h-12" preserveAspectRatio="none">
        <polygon points={areaPoints} fill={color} fillOpacity="0.12" />
        <polyline points={linePoints} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  )
}

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState<MetricSeries[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true

    const load = () => {
      fetchMetrics(30)
        .then((m) => { if (mounted) { setMetrics(m); setError(false) } })
        .catch(() => { if (mounted) setError(true) })
    }

    load()
    const interval = setInterval(load, 10000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  if (error && metrics.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary text-sm">
        Prometheus unavailable
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <h2 className="text-sm font-semibold text-text-secondary">System Metrics</h2>
      {metrics.map((s) => (
        <Sparkline key={s.label} series={s} />
      ))}
    </div>
  )
}
