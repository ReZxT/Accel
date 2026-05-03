const PROM = '/prometheus/api/v1'

interface PromResult {
  metric: Record<string, string>
  values?: [number, string][]
  value?: [number, string]
}

async function query(expr: string): Promise<PromResult[]> {
  const res = await fetch(`${PROM}/query?query=${encodeURIComponent(expr)}`)
  const json = await res.json()
  return json.data?.result ?? []
}

async function queryRange(expr: string, start: number, end: number, step: number): Promise<PromResult[]> {
  const params = new URLSearchParams({
    query: expr,
    start: start.toString(),
    end: end.toString(),
    step: step.toString(),
  })
  const res = await fetch(`${PROM}/query_range?${params}`)
  const json = await res.json()
  return json.data?.result ?? []
}

export interface MetricSeries {
  label: string
  unit: string
  current: number
  max: number
  points: { t: number; v: number }[]
}

const QUERIES: { key: string; label: string; unit: string; max: number; expr: string; rangeExpr?: string }[] = [
  {
    key: 'cpu',
    label: 'CPU',
    unit: '%',
    max: 100,
    expr: '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
    rangeExpr: '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
  },
  {
    key: 'ram',
    label: 'RAM',
    unit: '%',
    max: 100,
    expr: '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)',
    rangeExpr: '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)',
  },
  {
    key: 'gpu',
    label: 'GPU',
    unit: '%',
    max: 100,
    expr: 'amdgpu_utilization_percent',
    rangeExpr: 'amdgpu_utilization_percent',
  },
  {
    key: 'vram',
    label: 'VRAM',
    unit: '%',
    max: 100,
    expr: 'amdgpu_vram_used_percent',
    rangeExpr: 'amdgpu_vram_used_percent',
  },
  {
    key: 'gpu_temp',
    label: 'GPU Temp',
    unit: '°C',
    max: 110,
    expr: 'amdgpu_temperature_edge_celsius',
    rangeExpr: 'amdgpu_temperature_edge_celsius',
  },
  {
    key: 'gpu_power',
    label: 'GPU Power',
    unit: 'W',
    max: 186,
    expr: 'amdgpu_power_avg_watts',
    rangeExpr: 'amdgpu_power_avg_watts',
  },
  {
    key: 'disk',
    label: 'Disk /',
    unit: '%',
    max: 100,
    expr: '100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)',
    rangeExpr: '100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)',
  },
]

export async function fetchMetrics(rangeMins = 30): Promise<MetricSeries[]> {
  const now = Math.floor(Date.now() / 1000)
  const start = now - rangeMins * 60
  const step = Math.max(15, Math.floor(rangeMins * 60 / 120))

  const results = await Promise.all(
    QUERIES.map(async (q) => {
      const [instant, range] = await Promise.all([
        query(q.expr),
        queryRange(q.rangeExpr ?? q.expr, start, now, step),
      ])

      const current = instant[0]?.value ? parseFloat(instant[0].value[1]) : 0
      const points = (range[0]?.values ?? []).map(([t, v]) => ({ t, v: parseFloat(v) }))

      return {
        label: q.label,
        unit: q.unit,
        current: Math.round(current * 10) / 10,
        max: q.max,
        points,
      }
    })
  )

  return results
}
