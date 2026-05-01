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
