# Electron Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the existing React UI in an Electron shell that serves as the unified control plane for all Accel stack services.

**Architecture:** Electron main process manages services (process/docker/systemd), system tray, global hotkeys, and config persistence. React renderer communicates via typed IPC bridge with browser-fallback HTTP calls. Vite builds the renderer; electron-builder packages everything.

**Tech Stack:** Electron 35, Vite 8, React 19, TypeScript 6, Zustand 5, Tailwind CSS 4, electron-builder

---

## File Map

### New files — Electron main process (`ui/electron/`)

| File | Responsibility |
|------|---------------|
| `electron/main.ts` | App lifecycle, BrowserWindow, dev/prod URL loading, close-to-tray |
| `electron/preload.ts` | `contextBridge.exposeInMainWorld('accel', ...)` — typed IPC surface |
| `electron/types.ts` | Shared types: `ServiceDef`, `ServiceStatus`, `ServiceGroup`, `AccelConfig` |
| `electron/config.ts` | Read/write JSON settings to `~/.config/accel/` |
| `electron/services.ts` | `ServiceManager` — spawn, kill, health check, topological start |
| `electron/tray.ts` | `TrayManager` — system tray icon, context menu, health color |
| `electron/ipc-handlers.ts` | Register all IPC channels, wire to ServiceManager + ConfigStore |

### New files — Renderer (`ui/src/`)

| File | Responsibility |
|------|---------------|
| `src/api/electron.ts` | `isElectron()` detection, IPC wrappers with HTTP fallbacks |
| `src/stores/serviceStore.ts` | Zustand store for live service statuses |
| `src/types/electron.d.ts` | TypeScript declaration for `window.accel` |
| `src/components/services/ServiceDashboard.tsx` | Full-page service management view |
| `src/components/services/ServiceGroupCard.tsx` | Expandable group card with traffic lights |

### Modified files

| File | Change |
|------|--------|
| `ui/package.json` | Add electron, electron-builder, concurrently, wait-on; add scripts |
| `ui/vite.config.ts` | Add `base: './'` for file:// production loading |
| `ui/tsconfig.json` | Add electron tsconfig reference |
| `ui/.gitignore` | Add `release/` (electron-builder output) |
| `ui/src/types/index.ts` | Add `ServiceStatus`, `ServiceGroup` types |
| `ui/src/components/layout/LeftNav.tsx` | Add Services nav button |
| `ui/src/components/layout/AppShell.tsx` | Route to ServiceDashboard when active |
| `ui/src/stores/uiStore.ts` | Add `activeView` state for services page |

### New config files

| File | Responsibility |
|------|---------------|
| `ui/electron-builder.yml` | Packaging config (Linux target) |
| `ui/tsconfig.electron.json` | TypeScript config for electron/ directory |

---

## Task 1: Scaffold Electron + Dev Tooling

**Files:**
- Modify: `ui/package.json`
- Create: `ui/tsconfig.electron.json`
- Create: `ui/electron-builder.yml`
- Modify: `ui/.gitignore`
- Modify: `ui/vite.config.ts`

- [ ] **Step 1: Install Electron and dev dependencies**

```bash
cd /home/rezxt/bootstrap/ui
npm install --save-dev electron electron-builder concurrently wait-on
```

- [ ] **Step 2: Add scripts to package.json**

Add these scripts to `ui/package.json` (keep existing scripts):

```json
{
  "main": "dist-electron/main.js",
  "scripts": {
    "dev": "vite",
    "dev:electron": "concurrently -k \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "build": "tsc -b && vite build",
    "build:electron": "tsc -b && vite build && tsc -p tsconfig.electron.json && electron-builder",
    "lint": "eslint .",
    "preview": "vite preview"
  }
}
```

- [ ] **Step 3: Create tsconfig.electron.json**

Create `ui/tsconfig.electron.json`:

```json
{
  "compilerOptions": {
    "target": "es2023",
    "module": "commonjs",
    "moduleResolution": "node",
    "outDir": "dist-electron",
    "rootDir": "electron",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true
  },
  "include": ["electron"]
}
```

- [ ] **Step 4: Add electron tsconfig reference to root tsconfig.json**

Update `ui/tsconfig.json` to include the electron project reference:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" },
    { "path": "./tsconfig.electron.json" }
  ]
}
```

- [ ] **Step 5: Create electron-builder.yml**

Create `ui/electron-builder.yml`:

```yaml
appId: com.accel.desktop
productName: Accel
directories:
  output: release
files:
  - dist/**/*
  - dist-electron/**/*
linux:
  target:
    - AppImage
    - deb
  category: Utility
  icon: build/icon.png
```

- [ ] **Step 6: Update .gitignore**

Add to `ui/.gitignore`:

```
release
dist-electron
```

- [ ] **Step 7: Add base './' to Vite config for file:// compatibility**

In `ui/vite.config.ts`, add `base: './'` to the config so built assets resolve correctly when loaded via `file://` in production Electron:

```ts
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  // ... rest stays the same
})
```

- [ ] **Step 8: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit 2>&1 || echo "Expected: no input files (electron/ dir empty)"
```

- [ ] **Step 9: Commit**

```bash
git add ui/package.json ui/package-lock.json ui/tsconfig.json ui/tsconfig.electron.json ui/electron-builder.yml ui/.gitignore ui/vite.config.ts
git commit -m "feat(electron): scaffold Electron shell with dev tooling"
```

---

## Task 2: Electron Types

**Files:**
- Create: `ui/electron/types.ts`
- Modify: `ui/src/types/index.ts`
- Create: `ui/src/types/electron.d.ts`

- [ ] **Step 1: Create shared Electron types**

Create `ui/electron/types.ts`:

```ts
export type ServiceRuntime = 'process' | 'docker' | 'systemd'
export type ServiceHealth = 'healthy' | 'unhealthy' | 'stopped' | 'starting'
export type ServiceGroupId = 'inference' | 'core' | 'memory' | 'monitoring' | 'media' | 'dev'

export interface ServiceDef {
  id: string
  name: string
  runtime: ServiceRuntime
  command?: string
  compose?: string
  composeFile?: string
  unit?: string
  healthCheck: {
    url?: string
    interval: number
  }
  dependsOn: string[]
  autoStart: boolean
  group: ServiceGroupId
}

export interface ServiceStatus {
  id: string
  name: string
  group: ServiceGroupId
  health: ServiceHealth
  pid?: number
  uptime?: number
}

export interface AccelConfig {
  window: {
    width: number
    height: number
    x?: number
    y?: number
    maximized: boolean
  }
  hotkeys: {
    toggleWindow: string
  }
  autoStartGroups: ServiceGroupId[]
}

export const DEFAULT_CONFIG: AccelConfig = {
  window: {
    width: 1400,
    height: 900,
    maximized: false,
  },
  hotkeys: {
    toggleWindow: 'Super+Space',
  },
  autoStartGroups: [],
}
```

- [ ] **Step 2: Add service types to renderer types**

Add to the bottom of `ui/src/types/index.ts`:

```ts
export type ServiceRuntime = 'process' | 'docker' | 'systemd'
export type ServiceHealth = 'healthy' | 'unhealthy' | 'stopped' | 'starting'
export type ServiceGroupId = 'inference' | 'core' | 'memory' | 'monitoring' | 'media' | 'dev'

export interface ServiceStatus {
  id: string
  name: string
  group: ServiceGroupId
  health: ServiceHealth
  pid?: number
  uptime?: number
}
```

- [ ] **Step 3: Create window.accel TypeScript declaration**

Create `ui/src/types/electron.d.ts`:

```ts
import type { ServiceStatus } from './index'

interface AccelAPI {
  services: {
    list: () => Promise<ServiceStatus[]>
    start: (id: string) => Promise<{ ok: boolean; error?: string }>
    stop: (id: string) => Promise<{ ok: boolean; error?: string }>
    restart: (id: string) => Promise<{ ok: boolean; error?: string }>
    onStatus: (cb: (statuses: ServiceStatus[]) => void) => void
  }
  window: {
    minimize: () => void
    toggleMaximize: () => void
    close: () => void
  }
  config: {
    get: (key: string) => Promise<unknown>
    set: (key: string, val: unknown) => Promise<void>
  }
}

declare global {
  interface Window {
    accel?: AccelAPI
  }
}

export {}
```

- [ ] **Step 4: Verify types compile**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add ui/electron/types.ts ui/src/types/index.ts ui/src/types/electron.d.ts
git commit -m "feat(electron): add shared types for services, IPC bridge, and config"
```

---

## Task 3: ConfigStore

**Files:**
- Create: `ui/electron/config.ts`

- [ ] **Step 1: Create ConfigStore**

Create `ui/electron/config.ts`:

```ts
import * as fs from 'fs'
import * as path from 'path'
import { AccelConfig, DEFAULT_CONFIG } from './types'

const CONFIG_DIR = path.join(
  process.env.XDG_CONFIG_HOME || path.join(process.env.HOME || '/home/rezxt', '.config'),
  'accel'
)
const SETTINGS_PATH = path.join(CONFIG_DIR, 'settings.json')

export class ConfigStore {
  private config: AccelConfig

  constructor() {
    this.ensureDir()
    this.config = this.load()
  }

  private ensureDir(): void {
    if (!fs.existsSync(CONFIG_DIR)) {
      fs.mkdirSync(CONFIG_DIR, { recursive: true })
    }
  }

  private load(): AccelConfig {
    try {
      const raw = fs.readFileSync(SETTINGS_PATH, 'utf-8')
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
    } catch {
      return { ...DEFAULT_CONFIG }
    }
  }

  save(): void {
    fs.writeFileSync(SETTINGS_PATH, JSON.stringify(this.config, null, 2))
  }

  get<K extends keyof AccelConfig>(key: K): AccelConfig[K] {
    return this.config[key]
  }

  set<K extends keyof AccelConfig>(key: K, value: AccelConfig[K]): void {
    this.config[key] = value
    this.save()
  }

  getAll(): AccelConfig {
    return { ...this.config }
  }
}
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/electron/config.ts
git commit -m "feat(electron): add ConfigStore for persisting settings to ~/.config/accel/"
```

---

## Task 4: ServiceManager

**Files:**
- Create: `ui/electron/services.ts`

This is the largest and most important main-process module. It manages all Accel services across three runtimes.

- [ ] **Step 1: Create ServiceManager**

Create `ui/electron/services.ts`:

```ts
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
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/electron/services.ts
git commit -m "feat(electron): add ServiceManager with process/docker/systemd lifecycle"
```

---

## Task 5: TrayManager

**Files:**
- Create: `ui/electron/tray.ts`

- [ ] **Step 1: Create TrayManager**

Create `ui/electron/tray.ts`:

```ts
import { Tray, Menu, nativeImage, BrowserWindow } from 'electron'
import * as path from 'path'
import { ServiceStatus } from './types'

type HealthColor = 'green' | 'yellow' | 'red' | 'gray'

function createTrayIcon(color: HealthColor): Electron.NativeImage {
  const colors: Record<HealthColor, string> = {
    green: '#22c55e',
    yellow: '#fbbf24',
    red: '#f87171',
    gray: '#6b7280',
  }
  const fill = colors[color]

  const svg = `<svg width="16" height="16" xmlns="http://www.w3.org/2000/svg">
    <circle cx="8" cy="8" r="6" fill="${fill}" />
  </svg>`

  return nativeImage.createFromBuffer(Buffer.from(svg))
}

function computeColor(statuses: ServiceStatus[]): HealthColor {
  if (statuses.length === 0) return 'gray'
  const hasUnhealthy = statuses.some((s) => s.health === 'unhealthy')
  const hasHealthy = statuses.some((s) => s.health === 'healthy')
  if (hasUnhealthy) return 'red'
  if (hasHealthy) return 'yellow'
  return 'gray'
}

export class TrayManager {
  private tray: Tray
  private window: BrowserWindow
  private statuses: ServiceStatus[] = []

  constructor(window: BrowserWindow) {
    this.window = window
    this.tray = new Tray(createTrayIcon('gray'))
    this.tray.setToolTip('Accel')
    this.updateMenu()

    this.tray.on('click', () => {
      if (this.window.isVisible()) {
        this.window.hide()
      } else {
        this.window.show()
        this.window.focus()
      }
    })
  }

  updateStatuses(statuses: ServiceStatus[]): void {
    this.statuses = statuses
    const color = computeColor(statuses)
    this.tray.setImage(createTrayIcon(color))
    this.updateMenu()
  }

  private updateMenu(): void {
    const healthy = this.statuses.filter((s) => s.health === 'healthy').length
    const total = this.statuses.length
    const summary = total > 0 ? `Services: ${healthy}/${total} healthy` : 'No services configured'

    const menu = Menu.buildFromTemplate([
      { label: 'Show Accel', click: () => { this.window.show(); this.window.focus() } },
      { label: summary, enabled: false },
      { type: 'separator' },
      { label: 'Quit', click: () => { this.window.destroy(); process.exit(0) } },
    ])
    this.tray.setContextMenu(menu)
  }

  destroy(): void {
    this.tray.destroy()
  }
}
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/electron/tray.ts
git commit -m "feat(electron): add TrayManager with health-colored icon and context menu"
```

---

## Task 6: IPC Handlers

**Files:**
- Create: `ui/electron/ipc-handlers.ts`

- [ ] **Step 1: Create IPC handler registration**

Create `ui/electron/ipc-handlers.ts`:

```ts
import { ipcMain, BrowserWindow } from 'electron'
import { ServiceManager } from './services'
import { ConfigStore } from './config'

export function registerIpcHandlers(
  serviceManager: ServiceManager,
  configStore: ConfigStore,
  getWindow: () => BrowserWindow | null
): void {
  ipcMain.handle('services:list', () => {
    return serviceManager.list()
  })

  ipcMain.handle('services:start', async (_event, id: string) => {
    return serviceManager.start(id)
  })

  ipcMain.handle('services:stop', async (_event, id: string) => {
    return serviceManager.stop(id)
  })

  ipcMain.handle('services:restart', async (_event, id: string) => {
    return serviceManager.restart(id)
  })

  ipcMain.handle('config:get', (_event, key: string) => {
    return configStore.get(key as any)
  })

  ipcMain.handle('config:set', (_event, key: string, val: unknown) => {
    configStore.set(key as any, val as any)
  })

  ipcMain.on('window:minimize', () => {
    getWindow()?.minimize()
  })

  ipcMain.on('window:toggleMaximize', () => {
    const win = getWindow()
    if (win) {
      win.isMaximized() ? win.unmaximize() : win.maximize()
    }
  })

  ipcMain.on('window:close', () => {
    getWindow()?.hide()
  })

  serviceManager.setOnChange((statuses) => {
    const win = getWindow()
    if (win && !win.isDestroyed()) {
      win.webContents.send('services:status', statuses)
    }
  })
}
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/electron/ipc-handlers.ts
git commit -m "feat(electron): add IPC handlers bridging renderer to ServiceManager and ConfigStore"
```

---

## Task 7: Preload Script

**Files:**
- Create: `ui/electron/preload.ts`

- [ ] **Step 1: Create preload script**

Create `ui/electron/preload.ts`:

```ts
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('accel', {
  services: {
    list: () => ipcRenderer.invoke('services:list'),
    start: (id: string) => ipcRenderer.invoke('services:start', id),
    stop: (id: string) => ipcRenderer.invoke('services:stop', id),
    restart: (id: string) => ipcRenderer.invoke('services:restart', id),
    onStatus: (cb: (statuses: any[]) => void) => {
      ipcRenderer.on('services:status', (_event, data) => cb(data))
    },
  },
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    toggleMaximize: () => ipcRenderer.send('window:toggleMaximize'),
    close: () => ipcRenderer.send('window:close'),
  },
  config: {
    get: (key: string) => ipcRenderer.invoke('config:get', key),
    set: (key: string, val: unknown) => ipcRenderer.invoke('config:set', key, val),
  },
})
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/electron/preload.ts
git commit -m "feat(electron): add preload script exposing typed IPC bridge via contextBridge"
```

---

## Task 8: Main Process

**Files:**
- Create: `ui/electron/main.ts`

- [ ] **Step 1: Create main process entry**

Create `ui/electron/main.ts`:

```ts
import { app, BrowserWindow, globalShortcut } from 'electron'
import * as path from 'path'
import { ConfigStore } from './config'
import { ServiceManager } from './services'
import { TrayManager } from './tray'
import { registerIpcHandlers } from './ipc-handlers'

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let trayManager: TrayManager | null = null
const configStore = new ConfigStore()
const serviceManager = new ServiceManager()

function createWindow(): void {
  const windowConfig = configStore.get('window')

  mainWindow = new BrowserWindow({
    width: windowConfig.width,
    height: windowConfig.height,
    x: windowConfig.x,
    y: windowConfig.y,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (windowConfig.maximized) {
    mainWindow.maximize()
  }

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.on('close', (e) => {
    e.preventDefault()
    mainWindow?.hide()
  })

  mainWindow.on('resize', saveWindowState)
  mainWindow.on('move', saveWindowState)

  trayManager = new TrayManager(mainWindow)

  serviceManager.setOnChange((statuses) => {
    trayManager?.updateStatuses(statuses)
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('services:status', statuses)
    }
  })

  serviceManager.probeAll()
}

function saveWindowState(): void {
  if (!mainWindow) return
  const bounds = mainWindow.getBounds()
  configStore.set('window', {
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    maximized: mainWindow.isMaximized(),
  })
}

function registerHotkeys(): void {
  const hotkeys = configStore.get('hotkeys')

  globalShortcut.register(hotkeys.toggleWindow, () => {
    if (!mainWindow) return
    if (mainWindow.isVisible() && mainWindow.isFocused()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

app.whenReady().then(() => {
  registerIpcHandlers(serviceManager, configStore, () => mainWindow)
  createWindow()
  registerHotkeys()
})

app.on('window-all-closed', (e: Event) => {
  e.preventDefault()
})

app.on('activate', () => {
  mainWindow?.show()
})

app.on('before-quit', () => {
  serviceManager.destroy()
  trayManager?.destroy()
  mainWindow?.destroy()
})
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json --noEmit
```

- [ ] **Step 3: Build and test launch**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json
```

Then in a separate terminal, start Vite:
```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

Then test Electron:
```bash
cd /home/rezxt/bootstrap/ui && npx electron .
```

Expected: Electron window opens showing the React UI. System tray icon appears. Close button hides to tray.

- [ ] **Step 4: Commit**

```bash
git add ui/electron/main.ts
git commit -m "feat(electron): add main process with window manager, hotkeys, and service probe"
```

---

## Task 9: React IPC Wrapper

**Files:**
- Create: `ui/src/api/electron.ts`

- [ ] **Step 1: Create IPC wrapper with browser fallbacks**

Create `ui/src/api/electron.ts`:

```ts
import type { ServiceStatus } from '../types'

export function isElectron(): boolean {
  return typeof window !== 'undefined' && window.accel !== undefined
}

export const electronServices = {
  list: async (): Promise<ServiceStatus[]> => {
    if (isElectron()) return window.accel!.services.list()
    return []
  },

  start: async (id: string): Promise<{ ok: boolean; error?: string }> => {
    if (isElectron()) return window.accel!.services.start(id)
    return { ok: false, error: 'Not running in Electron' }
  },

  stop: async (id: string): Promise<{ ok: boolean; error?: string }> => {
    if (isElectron()) return window.accel!.services.stop(id)
    return { ok: false, error: 'Not running in Electron' }
  },

  restart: async (id: string): Promise<{ ok: boolean; error?: string }> => {
    if (isElectron()) return window.accel!.services.restart(id)
    return { ok: false, error: 'Not running in Electron' }
  },

  onStatus: (cb: (statuses: ServiceStatus[]) => void): void => {
    if (isElectron()) window.accel!.services.onStatus(cb)
  },
}

export const electronWindow = {
  minimize: (): void => {
    if (isElectron()) window.accel!.window.minimize()
  },
  toggleMaximize: (): void => {
    if (isElectron()) window.accel!.window.toggleMaximize()
  },
  close: (): void => {
    if (isElectron()) window.accel!.window.close()
  },
}
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/src/api/electron.ts
git commit -m "feat(electron): add React-side IPC wrapper with browser fallbacks"
```

---

## Task 10: Service Store

**Files:**
- Create: `ui/src/stores/serviceStore.ts`

- [ ] **Step 1: Create Zustand service store**

Create `ui/src/stores/serviceStore.ts`:

```ts
import { create } from 'zustand'
import type { ServiceStatus, ServiceGroupId } from '../types'
import { electronServices, isElectron } from '../api/electron'

interface ServiceStore {
  statuses: ServiceStatus[]
  loading: boolean
  initialized: boolean

  init: () => void
  refresh: () => Promise<void>
  startService: (id: string) => Promise<{ ok: boolean; error?: string }>
  stopService: (id: string) => Promise<{ ok: boolean; error?: string }>
  restartService: (id: string) => Promise<{ ok: boolean; error?: string }>

  byGroup: (group: ServiceGroupId) => ServiceStatus[]
}

export const useServiceStore = create<ServiceStore>((set, get) => ({
  statuses: [],
  loading: false,
  initialized: false,

  init: () => {
    if (get().initialized) return
    set({ initialized: true })

    electronServices.onStatus((statuses) => {
      set({ statuses })
    })

    get().refresh()
  },

  refresh: async () => {
    set({ loading: true })
    const statuses = await electronServices.list()
    set({ statuses, loading: false })
  },

  startService: async (id) => {
    const result = await electronServices.start(id)
    if (result.ok) await get().refresh()
    return result
  },

  stopService: async (id) => {
    const result = await electronServices.stop(id)
    if (result.ok) await get().refresh()
    return result
  },

  restartService: async (id) => {
    const result = await electronServices.restart(id)
    if (result.ok) await get().refresh()
    return result
  },

  byGroup: (group) => {
    return get().statuses.filter((s) => s.group === group)
  },
}))
```

- [ ] **Step 2: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add ui/src/stores/serviceStore.ts
git commit -m "feat(electron): add Zustand service store with IPC subscription"
```

---

## Task 11: Service Dashboard UI

**Files:**
- Create: `ui/src/components/services/ServiceGroupCard.tsx`
- Create: `ui/src/components/services/ServiceDashboard.tsx`

- [ ] **Step 1: Create ServiceGroupCard component**

Create `ui/src/components/services/ServiceGroupCard.tsx`:

```tsx
import { useState } from 'react'
import type { ServiceStatus, ServiceGroupId } from '../../types'
import { useServiceStore } from '../../stores/serviceStore'

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
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${HEALTH_COLORS[s.health]}`} />
                <span className="text-sm">{s.name}</span>
                <span className="text-xs text-text-tertiary">{s.health}</span>
              </div>
              <div className="flex gap-1">
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
    </div>
  )
}
```

- [ ] **Step 2: Create ServiceDashboard component**

Create `ui/src/components/services/ServiceDashboard.tsx`:

```tsx
import { useEffect } from 'react'
import { useServiceStore } from '../../stores/serviceStore'
import { isElectron } from '../../api/electron'
import ServiceGroupCard from './ServiceGroupCard'
import type { ServiceGroupId } from '../../types'

const GROUP_ORDER: ServiceGroupId[] = ['inference', 'core', 'memory', 'monitoring', 'media', 'dev']

export default function ServiceDashboard() {
  const init = useServiceStore((s) => s.init)
  const statuses = useServiceStore((s) => s.statuses)

  useEffect(() => { init() }, [init])

  if (!isElectron()) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-tertiary">
        <p className="text-sm">Service management is only available in the desktop app.</p>
      </div>
    )
  }

  const grouped = new Map<ServiceGroupId, typeof statuses>()
  for (const s of statuses) {
    const list = grouped.get(s.group) || []
    list.push(s)
    grouped.set(s.group, list)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h1 className="text-lg font-semibold mb-4">Services</h1>
      <div className="space-y-3 max-w-2xl">
        {GROUP_ORDER.map((group) => {
          const services = grouped.get(group)
          if (!services || services.length === 0) return null
          return <ServiceGroupCard key={group} group={group} services={services} />
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add ui/src/components/services/ServiceGroupCard.tsx ui/src/components/services/ServiceDashboard.tsx
git commit -m "feat(electron): add ServiceDashboard and ServiceGroupCard UI components"
```

---

## Task 12: Wire Dashboard into App Shell

**Files:**
- Modify: `ui/src/stores/uiStore.ts`
- Modify: `ui/src/components/layout/LeftNav.tsx`
- Modify: `ui/src/components/layout/AppShell.tsx`
- Modify: `ui/src/App.tsx`

- [ ] **Step 1: Add activeView to uiStore**

In `ui/src/stores/uiStore.ts`, add a `activeView` field to switch between chat and services. Add to the interface and store:

After the `activeOverlay` lines, add:

```ts
// Add to UIStore interface:
activeView: 'chat' | 'services'
setActiveView: (view: 'chat' | 'services') => void

// Add to create() body:
activeView: 'chat' as const,
setActiveView: (view) => set({ activeView: view }),
```

Full updated file:

```ts
import { create } from 'zustand'
import type { PanelType, OverlayType } from '../types'

interface UIStore {
  leftNavCollapsed: boolean
  toggleLeftNav: () => void

  rightPanelOpen: boolean
  rightPanelType: PanelType
  rightPanelData: unknown
  openPanel: (type: PanelType, data?: unknown) => void
  closePanel: () => void

  activeOverlay: OverlayType
  openOverlay: (type: OverlayType) => void
  closeOverlay: () => void

  activeView: 'chat' | 'services'
  setActiveView: (view: 'chat' | 'services') => void
}

export const useUIStore = create<UIStore>((set) => ({
  leftNavCollapsed: false,
  toggleLeftNav: () => set((s) => ({ leftNavCollapsed: !s.leftNavCollapsed })),

  rightPanelOpen: false,
  rightPanelType: null,
  rightPanelData: undefined,
  openPanel: (type, data) =>
    set({ rightPanelOpen: true, rightPanelType: type, rightPanelData: data }),
  closePanel: () =>
    set({ rightPanelOpen: false, rightPanelType: null, rightPanelData: undefined }),

  activeOverlay: null,
  openOverlay: (type) => set({ activeOverlay: type }),
  closeOverlay: () => set({ activeOverlay: null }),

  activeView: 'chat',
  setActiveView: (view) => set({ activeView: view }),
}))
```

- [ ] **Step 2: Add Services button to LeftNav**

In `ui/src/components/layout/LeftNav.tsx`, add a Services button above Settings in the bottom controls section. Add the import for `isElectron`:

```tsx
import { useUIStore } from '../../stores/uiStore'
import { isElectron } from '../../api/electron'
import SessionList from '../sessions/SessionList'

export default function LeftNav() {
  const collapsed = useUIStore((s) => s.leftNavCollapsed)
  const toggleLeftNav = useUIStore((s) => s.toggleLeftNav)
  const openOverlay = useUIStore((s) => s.openOverlay)
  const activeView = useUIStore((s) => s.activeView)
  const setActiveView = useUIStore((s) => s.setActiveView)

  return (
    <nav
      className={`flex flex-col bg-surface border-r border-border h-screen transition-[width] duration-200 ${
        collapsed ? 'w-16' : 'w-52'
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={toggleLeftNav}
        className="flex items-center justify-center h-12 text-text-tertiary hover:text-text-primary transition-colors"
        title={collapsed ? 'Expand' : 'Collapse'}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${collapsed ? 'rotate-180' : ''}`}
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto px-2">
        <SessionList collapsed={collapsed} />
      </div>

      {/* Bottom controls */}
      <div className="flex flex-col gap-1 p-2 border-t border-border">
        {isElectron() && (
          <button
            onClick={() => setActiveView(activeView === 'services' ? 'chat' : 'services')}
            className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
              activeView === 'services'
                ? 'text-accent bg-accent-soft'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
            }`}
            title="Services"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
            {!collapsed && <span className="text-sm">Services</span>}
          </button>
        )}
        <button
          onClick={() => openOverlay('settings')}
          className="flex items-center gap-3 px-3 py-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          title="Settings"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          {!collapsed && <span className="text-sm">Settings</span>}
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 3: Update App.tsx to route between chat and services**

Replace `ui/src/App.tsx`:

```tsx
import { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import MessageStream from './components/chat/MessageStream'
import InputBar from './components/chat/InputBar'
import SettingsDialog from './components/overlays/SettingsDialog'
import ServiceDashboard from './components/services/ServiceDashboard'
import { useChatStore } from './stores/chatStore'
import { useSessionStore } from './stores/sessionStore'
import { useUIStore } from './stores/uiStore'

export default function App() {
  const activeSession = useSessionStore((s) => s.activeSession)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const openPanel = useUIStore((s) => s.openPanel)
  const closePanel = useUIStore((s) => s.closePanel)
  const activeView = useUIStore((s) => s.activeView)

  useEffect(() => {
    loadHistory(activeSession)

    if (activeSession === 'architecture') {
      openPanel('canvas')
    } else if (activeSession === 'music') {
      openPanel('music')
    } else {
      closePanel()
    }
  }, [activeSession, loadHistory, openPanel, closePanel])

  useEffect(() => {
    const hash = window.location.hash.slice(1)
    if (hash) {
      const sessions = useSessionStore.getState().sessions
      if (sessions.some((s) => s.id === hash)) {
        useSessionStore.getState().switchSession(hash as any)
      }
    }
  }, [])

  return (
    <AppShell>
      {activeView === 'services' ? (
        <ServiceDashboard />
      ) : (
        <>
          <MessageStream />
          <InputBar />
        </>
      )}
      <SettingsDialog />
    </AppShell>
  )
}
```

- [ ] **Step 4: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 5: Test in browser**

Start the Vite dev server and verify:
1. Chat view works as before
2. Services button only appears in Electron (not in browser)
3. No console errors

```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

- [ ] **Step 6: Test in Electron**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.electron.json
npm run dev:electron
```

Expected:
- Electron window opens showing React UI
- Services button appears in left nav
- Clicking Services shows the dashboard with service group cards
- Traffic light dots reflect probed health
- Start/Stop/Restart buttons work
- System tray icon visible, right-click shows menu
- Close button hides to tray, click tray icon restores window

- [ ] **Step 7: Commit**

```bash
git add ui/src/stores/uiStore.ts ui/src/components/layout/LeftNav.tsx ui/src/App.tsx
git commit -m "feat(electron): wire service dashboard into app shell with view routing"
```

---

## Task 13: Custom Title Bar (frameless window controls)

**Files:**
- Create: `ui/src/components/layout/TitleBar.tsx`
- Modify: `ui/src/components/layout/AppShell.tsx`

Since `frame: false` is set in main.ts, the window has no native title bar. Add a draggable custom title bar with window controls.

- [ ] **Step 1: Create TitleBar component**

Create `ui/src/components/layout/TitleBar.tsx`:

```tsx
import { isElectron } from '../../api/electron'
import { electronWindow } from '../../api/electron'

export default function TitleBar() {
  if (!isElectron()) return null

  return (
    <div
      className="flex items-center justify-between h-9 bg-surface border-b border-border px-3 select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <span className="text-xs font-semibold text-text-tertiary">Accel</span>
      <div className="flex gap-1" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <button
          onClick={electronWindow.minimize}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-surface-hover text-text-tertiary hover:text-text-primary transition-colors"
        >
          <svg width="10" height="1" viewBox="0 0 10 1"><rect width="10" height="1" fill="currentColor" /></svg>
        </button>
        <button
          onClick={electronWindow.toggleMaximize}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-surface-hover text-text-tertiary hover:text-text-primary transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1"><rect x="0.5" y="0.5" width="9" height="9" /></svg>
        </button>
        <button
          onClick={electronWindow.close}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-error/20 text-text-tertiary hover:text-error transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.5"><line x1="1" y1="1" x2="9" y2="9" /><line x1="9" y1="1" x2="1" y2="9" /></svg>
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add TitleBar to AppShell**

Update `ui/src/components/layout/AppShell.tsx`:

```tsx
import { useEffect } from 'react'
import LeftNav from './LeftNav'
import RightPanel from './RightPanel'
import TitleBar from './TitleBar'
import { useUIStore } from '../../stores/uiStore'

interface Props {
  children: React.ReactNode
}

export default function AppShell({ children }: Props) {
  const closePanel = useUIStore((s) => s.closePanel)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closePanel])

  return (
    <div className="flex flex-col h-screen bg-bg-primary text-text-primary overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 min-h-0">
        <LeftNav />
        <main className="flex-1 flex flex-col min-w-0">{children}</main>
        <RightPanel />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -p tsconfig.app.json --noEmit
```

- [ ] **Step 4: Test**

In browser: TitleBar should not render (isElectron returns false), layout unchanged.

In Electron: draggable title bar at top, minimize/maximize/close buttons work, close hides to tray.

- [ ] **Step 5: Commit**

```bash
git add ui/src/components/layout/TitleBar.tsx ui/src/components/layout/AppShell.tsx
git commit -m "feat(electron): add custom draggable title bar with window controls"
```

---

## Task 14: Final Integration Test

- [ ] **Step 1: Full TypeScript check**

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -b
```

- [ ] **Step 2: Build production**

```bash
cd /home/rezxt/bootstrap/ui
npm run build
npx tsc -p tsconfig.electron.json
```

- [ ] **Step 3: Test Electron dev mode end-to-end**

```bash
cd /home/rezxt/bootstrap/ui
npm run dev:electron
```

Checklist:
- [ ] Window opens with custom title bar
- [ ] Title bar is draggable, buttons work (minimize, maximize, close-to-tray)
- [ ] Chat view loads, sessions switchable
- [ ] Services button in left nav (only visible in Electron)
- [ ] Services dashboard shows all service groups
- [ ] Expanding a group shows individual services with health status
- [ ] Start/Stop buttons trigger service lifecycle
- [ ] System tray icon present with context menu
- [ ] Tray icon color reflects service health
- [ ] Super+Space toggles window visibility
- [ ] Window state persists after restart

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix(electron): integration fixes from end-to-end testing"
```

- [ ] **Step 5: Final commit with all changes**

If no fixes were needed in step 4, skip this. Otherwise verify one more time:

```bash
cd /home/rezxt/bootstrap/ui
npx tsc -b && npx tsc -p tsconfig.electron.json --noEmit
```
