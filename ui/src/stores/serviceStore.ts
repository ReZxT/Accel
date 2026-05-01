import { create } from 'zustand'
import type { ServiceStatus, ServiceGroupId } from '../types'
import { electronServices } from '../api/electron'

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
