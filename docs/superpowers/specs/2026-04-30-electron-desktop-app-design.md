# Accel Desktop App — Electron Shell Design Spec

**Date:** 2026-04-30
**Status:** Approved (brainstorming)
**Scope:** Wrap the existing React UI in an Electron desktop app that serves as the unified control plane for the entire Accel stack.

## Goals

1. **Single control center** — one app to manage all Accel services, chat, tools, music, and (future) system monitoring
2. **Native powers** — global hotkeys, system tray, direct filesystem/process access, no browser permission dialogs
3. **Maximum extensibility** — plugin-ready architecture, new panels/services addable without touching core
4. **Browser still works** — the React UI remains functional in a browser when nginx is running; Electron adds capabilities on top

## Project Structure

```
bootstrap/
├── ui/                          # Existing React app (shared)
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts        # HTTP fetch (works in both)
│   │   │   └── electron.ts      # IPC wrappers, browser fallbacks
│   │   ├── components/
│   │   ├── stores/
│   │   └── ...
│   ├── electron/
│   │   ├── main.ts              # Electron main process
│   │   ├── preload.ts           # contextBridge exposing IPC
│   │   ├── services.ts          # ServiceManager
│   │   ├── tray.ts              # System tray
│   │   └── ipc-handlers.ts      # IPC channel handlers
│   ├── vite.config.ts
│   └── electron-builder.yml     # Packaging config
```

Electron code lives inside `ui/electron/` — one package, one build pipeline. Vite builds the renderer, electron-builder packages the whole thing.

## Main Process Architecture

```
Main Process
├── ServiceManager         # Start/stop/health-check all services
├── TrayManager            # System tray icon + quick menu
├── WindowManager          # Single main window, show/hide behavior
├── GlobalShortcuts        # Hotkeys (toggle window, push-to-talk)
├── IPC Handlers           # Bridge between renderer and main
└── ConfigStore            # Settings persistence
```

**Window behavior:**
- Single main window (BrowserWindow loading Vite dev server or built files)
- Close button minimizes to tray, not quit
- `Super+Space` (configurable) toggles window visibility
- Window state (size, position, maximized) persisted across restarts

**Tray:**
- Right-click menu: Show, services health summary, Quit
- Icon color reflects overall health: green (all up), yellow (some down), red (critical down)

## IPC Bridge

The renderer (React) never calls Node.js APIs directly. All native capabilities go through a typed IPC bridge.

**Preload script** exposes a typed API via `contextBridge`:

```ts
// preload.ts
contextBridge.exposeInMainWorld('accel', {
  services: {
    list: () => ipcRenderer.invoke('services:list'),
    start: (id: string) => ipcRenderer.invoke('services:start', id),
    stop: (id: string) => ipcRenderer.invoke('services:stop', id),
    restart: (id: string) => ipcRenderer.invoke('services:restart', id),
    onStatus: (cb: (statuses: ServiceStatus[]) => void) =>
      ipcRenderer.on('services:status', (_, data) => cb(data)),
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

**React-side wrapper** (`api/electron.ts`):

```ts
const isElectron = () => typeof window !== 'undefined' && 'accel' in window

export const services = {
  list: () => isElectron()
    ? window.accel.services.list()
    : apiFetch<ServiceStatus[]>('/api/services'),  // browser fallback
  start: (id: string) => isElectron()
    ? window.accel.services.start(id)
    : apiFetch(`/api/services/${id}/start`, { method: 'POST' }),
  // ...
}
```

Browser fallback calls HTTP APIs so the UI degrades gracefully when not in Electron.

## Service Manager

Every service is a first-class managed entity. No passive "external" category — Accel owns the lifecycle of everything it depends on.

### Service types by runtime

| Type | Examples | Start/Stop | Health Check |
|------|----------|------------|--------------|
| **Process** | llama-server, bootstrap, code-splitter | spawn/kill child process | HTTP ping or PID alive |
| **Docker** | Qdrant, embeddings, curator, nginx | `docker compose up/down` per service | container status + HTTP |
| **Systemd** | rocm-exporter | `systemctl start/stop` | `systemctl is-active` |

### Service definition schema

```ts
interface ServiceDef {
  id: string              // "llama-chat", "qdrant", "prometheus"
  name: string            // Display name
  runtime: "process" | "docker" | "systemd"
  command?: string        // For process type (with args)
  compose?: string        // docker-compose service name
  unit?: string           // systemd unit name
  healthCheck: {
    url?: string          // HTTP endpoint to ping
    interval: number      // ms between checks
  }
  dependsOn: string[]     // IDs — determines start order
  autoStart: boolean      // Launch on app start
  group: string           // UI grouping
}
```

### Service groups

- **Inference** — llama-chat, llama-embeddings, llama-curator
- **Core** — bootstrap, code-splitter, nginx
- **Memory** — Qdrant, MinIO
- **Monitoring** — Prometheus, Grafana, rocm-exporter, node-exporter
- **Media** — Navidrome, Feishin
- **Dev** — Forgejo, Portainer

Each group renders as a card with traffic-light status indicators. Expandable to show per-service controls (start/stop/restart), log tail, and resource usage.

### Model switching

Model switching is a special case of service management:
1. Stop current llama-chat process
2. Start new llama-chat process with different model args
3. UI shows a model selector dropdown that maps to predefined launch configs

Launch configs reference the existing start scripts (`start_chat_dimoe.sh`, `start_chat_gemma4.sh`, `start_chat_step3.sh`) or allow custom args.

### Startup sequence

Topological sort on `dependsOn`. Docker services can start in parallel (compose handles internal deps). Process services start sequentially respecting dependency order. User can customize which groups auto-start via settings.

### Path to system monitoring

Since Prometheus is a managed service and the app has IPC access, a future panel can query Prometheus directly (`/api/v1/query`) and render CPU/GPU/RAM/VRAM charts natively — no Grafana iframes needed. The service manager already correlates "which service is running" with resource usage.

## Voice Pipeline

Voice is managed as a service (the existing Python `voice/` pipeline). Deeper Electron integration (native audio capture, main-process wake word) deferred to the voice update.

Current state: Electron starts/stops the voice process, surfaces `/voice/status` and `/voice/toggle` through the IPC bridge. No architectural changes to the voice pipeline itself.

## Settings & Config

**Storage:**
- `~/.config/accel/settings.json` — window state, theme, auto-start groups, tool approval overrides, keybinds
- `~/.config/accel/services.json` — service registry definitions
- Plain JSON files via `electron-store` or raw fs — no database needed

**Settings UI** — React panel with sections:
- **Services** — auto-start toggles, per-service config
- **Appearance** — theme (dark default, future light mode)
- **Keybinds** — global hotkey customization
- **Tools** — approval policy overrides (existing functionality)
- **Voice** — toggle, device selection (when voice update lands)

**Global hotkeys:**
- `Super+Space` (configurable) — toggle window visibility
- `Super+Shift+V` — push-to-talk (future, when voice is updated)
- Registered via Electron `globalShortcut`, works when app is unfocused

## Nginx Toggle

Nginx is a managed Docker service like any other. When enabled, the React UI is accessible from browsers on other devices. When disabled, only the Electron app has access (Vite dev server or direct API calls). This is a simple start/stop in the service manager — no special logic needed.

## Dev Workflow

- `npm run dev` — starts Vite dev server + Electron in development mode, HMR on renderer, main process restarts on file change
- `npm run build` — Vite builds React, electron-builder packages everything
- `npm run start` — runs packaged Electron app
- Services are NOT bundled into the Electron binary — they run independently, Electron just manages their lifecycles
- The React UI remains fully functional in a browser (Electron adds native capabilities on top)

## Non-Goals (for this phase)

- Android app (separate project, later)
- Deep voice integration (waiting for voice pipeline update)
- Plugin marketplace / dynamic plugin loading (extensible architecture supports it, but no plugin API yet)
- Auto-update mechanism (local-first, manual updates fine for now)
- Multi-window support (single main window is sufficient)
