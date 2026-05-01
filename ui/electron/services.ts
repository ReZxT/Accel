import { spawn, ChildProcess, execSync } from 'child_process'
import { ServiceDef, ServiceStatus, ServiceHealth, ServiceGroupId } from './types'
import * as fs from 'fs'
import * as path from 'path'
import * as http from 'http'

const SERVICES_PATH = path.join(
  process.env.XDG_CONFIG_HOME || path.join(process.env.HOME || '/home/rezxt', '.config'),
  'accel',
  'services.json'
)

const DEFAULT_SERVICES: ServiceDef[] = [
  {
    id: 'llama-chat',
    name: 'Chat Model',
    runtime: 'process',
    command: '',
    healthCheck: { url: 'http://localhost:8080/health', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'inference',
  },
  {
    id: 'bootstrap',
    name: 'Bootstrap API',
    runtime: 'process',
    command: '/home/rezxt/bootstrap/.venv/bin/python /home/rezxt/bootstrap/main.py',
    healthCheck: { url: 'http://localhost:8100/health', interval: 5000 },
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'code-splitter',
    name: 'Code Splitter',
    runtime: 'process',
    command: '',
    healthCheck: { url: 'http://localhost:9200/health', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'nginx',
    name: 'Nginx',
    runtime: 'docker',
    compose: 'nginx',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:80', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'qdrant',
    name: 'Qdrant',
    runtime: 'docker',
    compose: 'qdrant',
    healthCheck: { url: 'http://localhost:6333/healthz', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'memory',
  },
  {
    id: 'minio',
    name: 'MinIO',
    runtime: 'docker',
    compose: 'minio',
    healthCheck: { url: 'http://localhost:9000/minio/health/live', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'memory',
  },
  {
    id: 'prometheus',
    name: 'Prometheus',
    runtime: 'docker',
    compose: 'prometheus',
    healthCheck: { url: 'http://localhost:9090/-/healthy', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'grafana',
    name: 'Grafana',
    runtime: 'docker',
    compose: 'grafana',
    healthCheck: { url: 'http://localhost:3001/api/health', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'navidrome',
    name: 'Navidrome',
    runtime: 'docker',
    compose: 'navidrome',
    healthCheck: { url: 'http://localhost:4533/rest/ping?f=json', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'media',
  },
  {
    id: 'rocm-exporter',
    name: 'ROCm Exporter',
    runtime: 'systemd',
    unit: 'rocm-exporter',
    healthCheck: { url: 'http://localhost:9101/metrics', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'forgejo',
    name: 'Forgejo',
    runtime: 'docker',
    compose: 'forgejo',
    healthCheck: { url: 'http://localhost:3000/api/v1/version', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'dev',
  },
  {
    id: 'portainer',
    name: 'Portainer',
    runtime: 'docker',
    compose: 'portainer',
    healthCheck: { url: 'http://localhost:9003/api/status', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'dev',
  },
]

export class ServiceManager {
  private defs: ServiceDef[]
  private statuses: Map<string, ServiceStatus> = new Map()
  private processes: Map<string, ChildProcess> = new Map()
  private healthTimers: Map<string, ReturnType<typeof setInterval>> = new Map()
  private onChange: ((statuses: ServiceStatus[]) => void) | null = null

  constructor() {
    this.defs = this.loadDefs()
    for (const def of this.defs) {
      this.statuses.set(def.id, {
        id: def.id,
        name: def.name,
        group: def.group,
        health: 'stopped',
      })
    }
  }

  private loadDefs(): ServiceDef[] {
    try {
      const raw = fs.readFileSync(SERVICES_PATH, 'utf-8')
      return JSON.parse(raw)
    } catch {
      const dir = path.dirname(SERVICES_PATH)
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
      fs.writeFileSync(SERVICES_PATH, JSON.stringify(DEFAULT_SERVICES, null, 2))
      return [...DEFAULT_SERVICES]
    }
  }

  setOnChange(cb: (statuses: ServiceStatus[]) => void): void {
    this.onChange = cb
  }

  private notify(): void {
    if (this.onChange) {
      this.onChange(this.list())
    }
  }

  list(): ServiceStatus[] {
    return Array.from(this.statuses.values())
  }

  getDef(id: string): ServiceDef | undefined {
    return this.defs.find((d) => d.id === id)
  }

  async start(id: string): Promise<{ ok: boolean; error?: string }> {
    const def = this.getDef(id)
    if (!def) return { ok: false, error: `Unknown service: ${id}` }

    const current = this.statuses.get(id)
    if (current && (current.health === 'healthy' || current.health === 'starting')) {
      return { ok: true }
    }

    this.updateHealth(id, 'starting')

    try {
      switch (def.runtime) {
        case 'process':
          this.startProcess(def)
          break
        case 'docker':
          this.startDocker(def)
          break
        case 'systemd':
          this.startSystemd(def)
          break
      }
      this.startHealthCheck(def)
      return { ok: true }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      this.updateHealth(id, 'unhealthy')
      return { ok: false, error: msg }
    }
  }

  async stop(id: string): Promise<{ ok: boolean; error?: string }> {
    const def = this.getDef(id)
    if (!def) return { ok: false, error: `Unknown service: ${id}` }

    this.stopHealthCheck(id)

    try {
      switch (def.runtime) {
        case 'process':
          this.stopProcess(id)
          break
        case 'docker':
          this.stopDocker(def)
          break
        case 'systemd':
          this.stopSystemd(def)
          break
      }
      this.updateHealth(id, 'stopped')
      return { ok: true }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      return { ok: false, error: msg }
    }
  }

  async restart(id: string): Promise<{ ok: boolean; error?: string }> {
    await this.stop(id)
    return this.start(id)
  }

  private startProcess(def: ServiceDef): void {
    if (!def.command) throw new Error(`No command configured for ${def.id}`)
    const parts = def.command.split(/\s+/)
    const child = spawn(parts[0], parts.slice(1), {
      stdio: 'ignore',
      detached: false,
      env: { ...process.env },
    })
    child.on('exit', () => {
      this.processes.delete(def.id)
      this.updateHealth(def.id, 'stopped')
    })
    this.processes.set(def.id, child)
  }

  private stopProcess(id: string): void {
    const child = this.processes.get(id)
    if (child && child.pid) {
      child.kill('SIGTERM')
      this.processes.delete(id)
    }
  }

  private startDocker(def: ServiceDef): void {
    const file = def.composeFile || '/home/rezxt/bootstrap/docker-compose.yml'
    execSync(`docker compose -f "${file}" up -d ${def.compose}`, { timeout: 30000 })
  }

  private stopDocker(def: ServiceDef): void {
    const file = def.composeFile || '/home/rezxt/bootstrap/docker-compose.yml'
    execSync(`docker compose -f "${file}" stop ${def.compose}`, { timeout: 30000 })
  }

  private startSystemd(def: ServiceDef): void {
    if (!def.unit) throw new Error(`No systemd unit configured for ${def.id}`)
    execSync(`systemctl --user start ${def.unit}`, { timeout: 10000 })
  }

  private stopSystemd(def: ServiceDef): void {
    if (!def.unit) throw new Error(`No systemd unit configured for ${def.id}`)
    execSync(`systemctl --user stop ${def.unit}`, { timeout: 10000 })
  }

  private startHealthCheck(def: ServiceDef): void {
    this.stopHealthCheck(def.id)
    if (!def.healthCheck.url) return

    const check = () => {
      this.httpPing(def.healthCheck.url!).then((ok) => {
        this.updateHealth(def.id, ok ? 'healthy' : 'unhealthy')
      })
    }

    check()
    const timer = setInterval(check, def.healthCheck.interval)
    this.healthTimers.set(def.id, timer)
  }

  private stopHealthCheck(id: string): void {
    const timer = this.healthTimers.get(id)
    if (timer) {
      clearInterval(timer)
      this.healthTimers.delete(id)
    }
  }

  private updateHealth(id: string, health: ServiceHealth): void {
    const current = this.statuses.get(id)
    if (current && current.health !== health) {
      current.health = health
      this.notify()
    }
  }

  private httpPing(url: string): Promise<boolean> {
    return new Promise((resolve) => {
      const req = http.get(url, { timeout: 3000 }, (res) => {
        resolve(res.statusCode !== undefined && res.statusCode < 500)
        res.resume()
      })
      req.on('error', () => resolve(false))
      req.on('timeout', () => {
        req.destroy()
        resolve(false)
      })
    })
  }

  probeAll(): void {
    for (const def of this.defs) {
      if (def.healthCheck.url) {
        this.httpPing(def.healthCheck.url).then((ok) => {
          this.updateHealth(def.id, ok ? 'healthy' : 'stopped')
          if (ok) this.startHealthCheck(def)
        })
      }
    }
  }

  destroy(): void {
    for (const timer of this.healthTimers.values()) {
      clearInterval(timer)
    }
    this.healthTimers.clear()
  }
}
