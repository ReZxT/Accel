import { create } from 'zustand'
import type { OverlayType, MessageImage, MessageFile, PanelMode, OpenPanelPayload } from '../types'

interface UIStore {
  leftNavCollapsed: boolean
  toggleLeftNav: () => void

  panelOpen: boolean
  panelMode: PanelMode
  panelPayload: OpenPanelPayload | undefined
  openPanelMode: (mode: PanelMode, payload?: OpenPanelPayload) => void
  togglePanel: () => void
  closePanel: () => void

  activeOverlay: OverlayType
  openOverlay: (type: OverlayType) => void
  closeOverlay: () => void

  activeView: 'chat' | 'services'
  setActiveView: (view: 'chat' | 'services') => void

  lightboxSrc: string | null
  openLightbox: (src: string) => void
  closeLightbox: () => void

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

  panelOpen: false,
  panelMode: 'music',
  panelPayload: undefined,
  openPanelMode: (mode, payload) =>
    set({ panelOpen: true, panelMode: mode, panelPayload: payload }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen, panelPayload: s.panelOpen ? undefined : s.panelPayload })),
  closePanel: () => set({ panelOpen: false, panelPayload: undefined }),

  activeOverlay: null,
  openOverlay: (type) => set({ activeOverlay: type }),
  closeOverlay: () => set({ activeOverlay: null }),

  activeView: 'chat',
  setActiveView: (view) => set({ activeView: view }),

  lightboxSrc: null,
  openLightbox: (src) => set({ lightboxSrc: src }),
  closeLightbox: () => set({ lightboxSrc: null }),

  pendingImages: [],
  pendingFiles: [],
  addPendingAttachments: (images, files) =>
    set((s) => ({ pendingImages: [...s.pendingImages, ...images], pendingFiles: [...s.pendingFiles, ...files] })),
  removeImage: (i) => set((s) => ({ pendingImages: s.pendingImages.filter((_, j) => j !== i) })),
  removeFile: (i) => set((s) => ({ pendingFiles: s.pendingFiles.filter((_, j) => j !== i) })),
  clearAttachments: () => set({ pendingImages: [], pendingFiles: [] }),
}))
