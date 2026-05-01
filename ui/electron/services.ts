import { spawn, ChildProcess } from 'child_process'
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
    command: 'llama-server -m /mnt/WD/Models/Qwen3.5-9B-Deckard-Claude-DIMOE-Uncensored-Heretic-Thinking.Q5_K_M.gguf --mmproj /mnt/WD/Models/Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED.mmproj-Q8_0.gguf -c 65536 --host 0.0.0.0 --port 8080 -ngl 99 --jinja',
    healthCheck: { url: 'http://localhost:8080/health', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'inference',
    accelerator: 'gpu',
  },
  {
    id: 'llama-chat-docker',
    name: 'Chat Model (Container)',
    runtime: 'docker',
    compose: 'llama-chat-gpu',
    composeFile: '/home/rezxt/ai-stack/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8080/health', interval: 10000 },
    dependsOn: [],
    autoStart: false,
    group: 'inference',
    accelerator: 'gpu',
  },
  {
    id: 'llama-curator',
    name: 'Curator Model',
    runtime: 'docker',
    compose: 'curator',
    composeFile: '/home/rezxt/ai-stack/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8082/health', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'inference',
    accelerator: 'cpu',
  },
  {
    id: 'llama-embeddings',
    name: 'Embeddings Model',
    runtime: 'docker',
    compose: 'embeddings',
    composeFile: '/home/rezxt/ai-stack/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8081/health', interval: 15000 },
    dependsOn: [],
    autoStart: false,
    group: 'inference',
    accelerator: 'cpu',
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

const MAX_RESTARTS = 5
const RESTART_BACKOFF_MS = [2000, 4000, 8000, 16000, 30000]

export class ServiceManager {
  private defs: ServiceDef[]
  private statuses: Map<string, ServiceStatus> = new Map()
  private processes: Map<string, ChildProcess> = new Map()
  private healthTimers: Map<string, ReturnType<typeof setInterval>> = new Map()
  private restartCounts: Map<string, number> = new Map()
  private restartTimers: Map<string, ReturnType<typeof setTimeout>> = new Map()
  private onChange: ((statuses: ServiceStatus[]) => void) | null = null

  constructor() {
    this.defs = this.loadDefs()
    for (const def of this.defs) {
      this.statuses.set(def.id, {
        id: def.id,
        name: def.name,
        group: def.group,
        health: 'stopped',
        accelerator: def.accelerator,
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
          await this.startDocker(def)
          break
        case 'systemd':
          await this.startSystemd(def)
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
          await this.stopDocker(def)
          break
        case 'systemd':
          await this.stopSystemd(def)
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

  private startProcess(def: ServiceDef, isRestart = false): void {
    if (!def.command) throw new Error(`No command configured for ${def.id}`)
    if (!isRestart) this.restartCounts.set(def.id, 0)

    const parts = def.command.split(/\s+/)
    const child = spawn(parts[0], parts.slice(1), {
      stdio: 'ignore',
      detached: true,  // own process group — OOM killer won't take Electron with it
      env: { ...process.env },
    })
    child.unref()  // don't keep Electron's event loop alive waiting for child
    child.on('exit', (code) => {
      this.processes.delete(def.id)
      const intentional = !this.healthTimers.has(def.id)
      if (intentional) {
        this.updateHealth(def.id, 'stopped')
        return
      }
      // Unexpected exit — auto-restart with backoff
      const attempts = (this.restartCounts.get(def.id) ?? 0)
      if (attempts >= MAX_RESTARTS) {
        this.updateHealth(def.id, 'unhealthy')
        this.stopHealthCheck(def.id)
        return
      }
      const delay = RESTART_BACKOFF_MS[Math.min(attempts, RESTART_BACKOFF_MS.length - 1)]
      this.restartCounts.set(def.id, attempts + 1)
      this.updateHealth(def.id, 'starting')
      const timer = setTimeout(() => {
        this.restartTimers.delete(def.id)
        this.startProcess(def, true)
      }, delay)
      this.restartTimers.set(def.id, timer)
    })
    this.processes.set(def.id, child)
  }

  private stopProcess(id: string): void {
    // Cancel any pending restart before stopping
    const timer = this.restartTimers.get(id)
    if (timer) {
      clearTimeout(timer)
      this.restartTimers.delete(id)
    }
    this.restartCounts.delete(id)
    const child = this.processes.get(id)
    if (child && child.pid) {
      child.kill('SIGTERM')
      this.processes.delete(id)
    }
  }

  private spawnDetached(cmd: string, args: string[]): Promise<void> {
    return new Promise((resolve, reject) => {
      const child = spawn(cmd, args, { stdio: 'ignore', detached: true })
      child.unref()
      child.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`))))
      child.on('error', reject)
    })
  }

  private startDocker(def: ServiceDef): Promise<void> {
    const file = def.composeFile || '/home/rezxt/bootstrap/docker-compose.yml'
    return this.spawnDetached('docker', ['compose', '-f', file, 'up', '-d', def.compose!])
  }

  private stopDocker(def: ServiceDef): Promise<void> {
    const file = def.composeFile || '/home/rezxt/bootstrap/docker-compose.yml'
    return this.spawnDetached('docker', ['compose', '-f', file, 'stop', def.compose!])
  }

  private startSystemd(def: ServiceDef): Promise<void> {
    if (!def.unit) return Promise.reject(new Error(`No systemd unit configured for ${def.id}`))
    return this.spawnDetached('systemctl', ['--user', 'start', def.unit])
  }

  private stopSystemd(def: ServiceDef): Promise<void> {
    if (!def.unit) return Promise.reject(new Error(`No systemd unit configured for ${def.id}`))
    return this.spawnDetached('systemctl', ['--user', 'stop', def.unit])
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
    if (health === 'healthy') this.restartCounts.set(id, 0)
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
    for (const timer of this.healthTimers.values()) clearInterval(timer)
    for (const timer of this.restartTimers.values()) clearTimeout(timer)
    this.healthTimers.clear()
    this.restartTimers.clear()
  }
}
