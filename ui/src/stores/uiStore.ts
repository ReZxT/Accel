import { create } from 'zustand'
import type { PanelType, OverlayType, MessageImage, MessageFile } from '../types'

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

  pendingImages: MessageImage[]
  pendingFiles: MessageFile[]
  addPendingAttachments: (images: MessageImage[], files: MessageFile[]) => void
  removeImage: (i: number) => void
  removeFile: (i: number) => void
  clearAttachments: () => void
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

  pendingImages: [],
  pendingFiles: [],
  addPendingAttachments: (images, files) =>
    set((s) => ({ pendingImages: [...s.pendingImages, ...images], pendingFiles: [...s.pendingFiles, ...files] })),
  removeImage: (i) => set((s) => ({ pendingImages: s.pendingImages.filter((_, j) => j !== i) })),
  removeFile: (i) => set((s) => ({ pendingFiles: s.pendingFiles.filter((_, j) => j !== i) })),
  clearAttachments: () => set({ pendingImages: [], pendingFiles: [] }),
}))
