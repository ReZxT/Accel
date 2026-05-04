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
    id: 'llama-chat-docker',
    name: 'Chat Model',
    runtime: 'docker',
    compose: 'llama-chat-gpu',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8080/health', interval: 10000 },
    ports: [8080],
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
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8082/health', interval: 15000 },
    ports: [8082],
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
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8081/health', interval: 15000 },
    ports: [8081],
    dependsOn: [],
    autoStart: false,
    group: 'inference',
    accelerator: 'gpu',
  },
  {
    id: 'bootstrap',
    name: 'Bootstrap API',
    runtime: 'process',
    command: '/home/rezxt/bootstrap/.venv/bin/python /home/rezxt/bootstrap/main.py',
    healthCheck: { url: 'http://localhost:8100/health', interval: 5000 },
    ports: [8100],
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'code-splitter',
    name: 'Code Splitter',
    runtime: 'docker',
    compose: 'code-splitter',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9200/health', interval: 10000 },
    ports: [9200],
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
    ports: [80],
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'searxng',
    name: 'SearXNG',
    runtime: 'docker',
    compose: 'searxng',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:8888', interval: 15000 },
    ports: [8888],
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'playwright',
    name: 'Playwright',
    runtime: 'docker',
    compose: 'playwright',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9300/health', interval: 15000 },
    ports: [9300],
    dependsOn: [],
    autoStart: false,
    group: 'core',
  },
  {
    id: 'qdrant',
    name: 'Qdrant',
    runtime: 'docker',
    compose: 'qdrant',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:6333/healthz', interval: 10000 },
    ports: [6333, 6334],
    dependsOn: [],
    autoStart: false,
    group: 'memory',
  },
  {
    id: 'minio',
    name: 'MinIO',
    runtime: 'docker',
    compose: 'minio',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9000/minio/health/live', interval: 10000 },
    ports: [9000, 9001],
    dependsOn: [],
    autoStart: false,
    group: 'memory',
  },
  {
    id: 'prometheus',
    name: 'Prometheus',
    runtime: 'docker',
    compose: 'prometheus',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9090/-/healthy', interval: 15000 },
    ports: [9090],
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'grafana',
    name: 'Grafana',
    runtime: 'docker',
    compose: 'grafana',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:3001/api/health', interval: 15000 },
    ports: [3001],
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'rocm-exporter',
    name: 'ROCm Exporter',
    runtime: 'systemd',
    unit: 'rocm-exporter',
    healthCheck: { url: 'http://localhost:9101/metrics', interval: 15000 },
    ports: [9101],
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'node-exporter',
    name: 'Node Exporter',
    runtime: 'docker',
    compose: 'node-exporter',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9100/metrics', interval: 30000 },
    ports: [9100],
    dependsOn: [],
    autoStart: false,
    group: 'monitoring',
  },
  {
    id: 'navidrome',
    name: 'Navidrome',
    runtime: 'docker',
    compose: 'navidrome',
    composeFile: '/mnt/WD/Docker/navidrome/docker-compose.yml',
    healthCheck: { url: 'http://localhost:4533/rest/ping?f=json', interval: 15000 },
    ports: [4533],
    dependsOn: [],
    autoStart: false,
    group: 'media',
  },
  {
    id: 'forgejo',
    name: 'Forgejo',
    runtime: 'docker',
    compose: 'forgejo',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:3000/api/v1/version', interval: 15000 },
    ports: [3000],
    dependsOn: [],
    autoStart: false,
    group: 'dev',
  },
  {
    id: 'portainer',
    name: 'Portainer',
    runtime: 'docker',
    compose: 'portainer',
    composeFile: '/home/rezxt/bootstrap/docker-compose.yml',
    healthCheck: { url: 'http://localhost:9003/api/status', interval: 15000 },
    ports: [9003],
    dependsOn: [],
    autoStart: false,
    group: 'dev',
  },
]

const MAX_RESTARTS = 5
const RESTART_BACKOFF_MS = [2000, 4000, 8000, 16000, 30000]
const FAILURES_BEFORE_UNHEALTHY = 3

export class ServiceManager {
  private defs: ServiceDef[]
  private statuses: Map<string, ServiceStatus> = new Map()
  private processes: Map<string, ChildProcess> = new Map()
  private healthTimers: Map<string, ReturnType<typeof setInterval>> = new Map()
  private restartCounts: Map<string, number> = new Map()
  private restartTimers: Map<string, ReturnType<typeof setTimeout>> = new Map()
  private healthFailures: Map<string, number> = new Map()
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
        ports: def.ports,
      })
    }
  }

  private loadDefs(): ServiceDef[] {
    try {
      const raw = fs.readFileSync(SERVICES_PATH, 'utf-8')
      const saved: ServiceDef[] = JSON.parse(raw)
      const savedIds = new Set(saved.map((s) => s.id))
      const merged = [...saved, ...DEFAULT_SERVICES.filter((d) => !savedIds.has(d.id))]
      return merged
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

    // If the port is already responding, adopt the external process instead of spawning a duplicate
    if (def.healthCheck.url) {
      const alreadyUp = await this.httpPing(def.healthCheck.url)
      if (alreadyUp) {
        this.updateHealth(id, 'healthy')
        this.startHealthCheck(def)
        return { ok: true }
      }
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
    const status = this.statuses.get(id)
    if (status) status.modelName = undefined

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

  async getLogs(id: string): Promise<string> {
    const def = this.getDef(id)
    if (!def) return 'Unknown service'
    return new Promise((resolve) => {
      let output = ''
      let child: ReturnType<typeof spawn>
      if (def.runtime === 'docker' && def.compose) {
        const file = def.composeFile || '/home/rezxt/ai-stack/docker-compose.yml'
        child = spawn('docker', ['compose', '-f', file, 'logs', def.compose, '--tail', '300', '--no-color'], { stdio: ['ignore', 'pipe', 'pipe'] })
      } else if (def.runtime === 'systemd' && def.unit) {
        child = spawn('journalctl', ['-u', def.unit, '-n', '300', '--no-pager', '--no-hostname'], { stdio: ['ignore', 'pipe', 'pipe'] })
      } else {
        return resolve('Logs not available for this service type (process without stdio capture).')
      }
      child.stdout?.on('data', (d: Buffer) => { output += d.toString() })
      child.stderr?.on('data', (d: Buffer) => { output += d.toString() })
      child.on('close', () => resolve(output.trim() || '(no output)'))
      child.on('error', (e: Error) => resolve(`Error: ${e.message}`))
    })
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
    } else {
      const def = this.getDef(id)
      const port = def?.ports?.[0]
      if (port) {
        spawn('fuser', ['-k', `${port}/tcp`], { stdio: 'ignore' })
      }
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
    const file = def.composeFile || '/home/rezxt/ai-stack/docker-compose.yml'
    return this.spawnDetached('docker', ['compose', '-f', file, 'up', '-d', def.compose!])
  }

  private stopDocker(def: ServiceDef): Promise<void> {
    const file = def.composeFile || '/home/rezxt/ai-stack/docker-compose.yml'
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

  private dockerContainerRunning(def: ServiceDef): Promise<boolean> {
    return new Promise((resolve) => {
      const file = def.composeFile || '/home/rezxt/ai-stack/docker-compose.yml'
      const child = spawn('docker', ['compose', '-f', file, 'ps', def.compose!, '--format', 'json'], {
        stdio: ['ignore', 'pipe', 'ignore'],
      })
      let out = ''
      child.stdout?.on('data', (d: Buffer) => { out += d.toString() })
      child.on('close', () => {
        try {
          const running = out.trim().split('\n').filter(Boolean).some((line) => {
            const obj = JSON.parse(line)
            return obj.State === 'running'
          })
          resolve(running)
        } catch {
          resolve(false)
        }
      })
      child.on('error', () => resolve(false))
    })
  }

  private ping(def: ServiceDef): Promise<boolean> {
    if (!def.healthCheck.url) return Promise.resolve(false)
    const httpCheck = this.httpPing(def.healthCheck.url)
    if (def.runtime !== 'docker' || !def.compose) return httpCheck
    return Promise.all([httpCheck, this.dockerContainerRunning(def)]).then(([ok, running]) => ok && running)
  }

  private startHealthCheck(def: ServiceDef): void {
    this.stopHealthCheck(def.id)
    if (!def.healthCheck.url) return

    const check = () => {
      this.ping(def).then((ok) => {
        if (ok) {
          this.healthFailures.set(def.id, 0)
          this.updateHealth(def.id, 'healthy')
          if (def.group === 'inference') this.fetchModelName(def)
        } else {
          const fails = (this.healthFailures.get(def.id) ?? 0) + 1
          this.healthFailures.set(def.id, fails)
          if (fails >= FAILURES_BEFORE_UNHEALTHY) {
            this.updateHealth(def.id, 'unhealthy')
          }
        }
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
    this.healthFailures.delete(id)
  }

  private updateHealth(id: string, health: ServiceHealth): void {
    const current = this.statuses.get(id)
    if (health === 'healthy') this.restartCounts.set(id, 0)
    if (current && current.health !== health) {
      current.health = health
      this.notify()
    }
  }

  private fetchModelName(def: ServiceDef): void {
    const status = this.statuses.get(def.id)
    if (!status || status.modelName) return
    const port = def.ports?.[0]
    if (!port) return
    const url = `http://localhost:${port}/v1/models`
    http.get(url, { timeout: 3000 }, (res) => {
      let data = ''
      res.on('data', (chunk: Buffer) => { data += chunk.toString() })
      res.on('end', () => {
        try {
          const json = JSON.parse(data)
          const name = json.data?.[0]?.id || json.models?.[0]?.model
          if (name && status) {
            status.modelName = name.replace(/\.gguf$/, '')
            this.notify()
          }
        } catch {}
      })
    }).on('error', () => {})
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
        this.ping(def).then((ok) => {
          this.updateHealth(def.id, ok ? 'healthy' : 'stopped')
          if (ok) {
            this.startHealthCheck(def)
            if (def.group === 'inference') this.fetchModelName(def)
          }
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
