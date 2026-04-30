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
}))
