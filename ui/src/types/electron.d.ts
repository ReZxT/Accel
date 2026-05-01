import type { ServiceStatus } from './index'

interface AccelAPI {
  services: {
    list: () => Promise<ServiceStatus[]>
    start: (id: string) => Promise<{ ok: boolean; error?: string }>
    stop: (id: string) => Promise<{ ok: boolean; error?: string }>
    restart: (id: string) => Promise<{ ok: boolean; error?: string }>
    onStatus: (cb: (statuses: ServiceStatus[]) => void) => void
    logs: (id: string) => Promise<string>
  }
  window: {
    minimize: () => void
    toggleMaximize: () => void
    close: () => void
    openDevTools: () => void
    onFocus: (cb: () => void) => void
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
