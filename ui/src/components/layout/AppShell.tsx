import { useRef, useEffect, useState, useCallback } from 'react'
import LeftNav from './LeftNav'
import RightPanel from './RightPanel'
import TitleBar from './TitleBar'
import { useUIStore } from '../../stores/uiStore'
import { usePlayerStore } from '../../stores/playerStore'
import type { MessageImage, MessageFile } from '../../types'

const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const LANGUAGE_MAP: Record<string, string> = {
  ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
  py: 'python', rs: 'rust', go: 'go', cpp: 'cpp', c: 'c', cs: 'csharp',
  java: 'java', rb: 'ruby', sh: 'bash', md: 'markdown', json: 'json',
  yaml: 'yaml', yml: 'yaml', toml: 'toml', html: 'html', css: 'css',
}

function Lightbox() {
  const src = useUIStore((s) => s.lightboxSrc)
  const close = useUIStore((s) => s.closeLightbox)

  useEffect(() => {
    if (!src) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [src, close])

  if (!src) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm cursor-pointer"
      onClick={close}
    >
      <img
        src={src}
        alt="Preview"
        className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl cursor-default"
        onClick={(e) => e.stopPropagation()}
      />
      <button
        onClick={close}
        className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors cursor-pointer"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
      </button>
    </div>
  )
}

function MiniPlayer() {
  const np = usePlayerStore((s) => s.nowPlaying)
  const queue = usePlayerStore((s) => s.queue)
  const isPlaying = usePlayerStore((s) => s.isPlaying)
  const playPause = usePlayerStore((s) => s.playPause)
  const next = usePlayerStore((s) => s.next)
  const previous = usePlayerStore((s) => s.previous)
  const panelMode = useUIStore((s) => s.panelMode)
  const panelOpen = useUIStore((s) => s.panelOpen)
  const openPanelMode = useUIStore((s) => s.openPanelMode)

  if (!np || (!queue.length && np.status === 'stopped')) return null
  if (panelOpen && panelMode === 'music') return null

  const progress = np.position / Math.max(np.length, 1)

  return (
    <div className="relative flex items-center gap-3 px-3 py-1.5 bg-surface border-t border-border flex-shrink-0">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-border">
        <div className="h-full bg-accent transition-all" style={{ width: `${progress * 100}%` }} />
      </div>
      {np.art_url ? (
        <img src={np.art_url} className="w-8 h-8 rounded object-cover flex-shrink-0" />
      ) : (
        <div className="w-8 h-8 rounded bg-surface-hover flex items-center justify-center flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-tertiary">
            <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
          </svg>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium text-text-primary truncate">{np.title || 'Nothing playing'}</div>
        <div className="text-[10px] text-text-tertiary truncate">{np.artist}</div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button onClick={previous} className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="19 20 9 12 19 4 19 20" /><line x1="5" y1="19" x2="5" y2="5" /></svg>
        </button>
        <button onClick={playPause} className="w-7 h-7 rounded-full bg-accent flex items-center justify-center hover:bg-violet-500 transition-colors cursor-pointer">
          {isPlaying || np.status === 'playing' ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-white"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-white"><polygon points="5 3 19 12 5 21 5 3" /></svg>
          )}
        </button>
        <button onClick={next} className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 4 15 12 5 20 5 4" /><line x1="19" y1="5" x2="19" y2="19" /></svg>
        </button>
      </div>
      <button
        onClick={() => openPanelMode('music')}
        className="text-text-tertiary hover:text-accent transition-colors cursor-pointer ml-1"
        title="Open music panel"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg>
      </button>
    </div>
  )
}

interface Props {
  children: React.ReactNode
}

export default function AppShell({ children }: Props) {
  const addPendingAttachments = useUIStore((s) => s.addPendingAttachments)
  const setAudioElement = usePlayerStore((s) => s.setAudioElement)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [dragging, setDragging] = useState(false)
  const dragCounter = useRef(0)

  useEffect(() => {
    if (audioRef.current) setAudioElement(audioRef.current)
  }, [setAudioElement])

  const processFiles = useCallback(async (fileList: FileList) => {
    const imgs: MessageImage[] = []
    const files: MessageFile[] = []
    for (const file of Array.from(fileList)) {
      if (IMAGE_TYPES.has(file.type)) {
        const base64 = await new Promise<string>((res, rej) => {
          const r = new FileReader()
          r.onload = () => res((r.result as string).split(',')[1])
          r.onerror = rej
          r.readAsDataURL(file)
        })
        imgs.push({ base64, name: file.name, type: file.type, dataUrl: `data:${file.type};base64,${base64}` })
      } else {
        const content = await new Promise<string>((res, rej) => {
          const r = new FileReader()
          r.onload = () => res(r.result as string)
          r.onerror = rej
          r.readAsText(file)
        })
        const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
        files.push({ content, name: file.name, language: LANGUAGE_MAP[ext] ?? '' })
      }
    }
    addPendingAttachments(imgs, files)
  }, [addPendingAttachments])

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current++
    if (e.dataTransfer.types.includes('Files')) setDragging(true)
  }, [])

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current--
    if (dragCounter.current === 0) setDragging(false)
  }, [])

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault() }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current = 0
    setDragging(false)
    if (e.dataTransfer.files.length) processFiles(e.dataTransfer.files)
  }, [processFiles])

  return (
    <div
      className="flex flex-col h-screen bg-bg-primary text-text-primary overflow-hidden"
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <audio ref={audioRef} className="hidden" />
      <TitleBar />
      <div className="flex flex-1 min-h-0 relative">
        <LeftNav />
        <main className="flex-1 flex flex-col min-w-0">{children}</main>
        <RightPanel />

        {dragging && (
          <div className="absolute inset-0 z-40 flex items-center justify-center pointer-events-none">
            <div className="absolute inset-2 rounded-xl border-2 border-dashed border-accent bg-accent/5 backdrop-blur-sm" />
            <div className="relative flex flex-col items-center gap-3 text-accent">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
              </svg>
              <span className="text-sm font-medium">Drop files to attach</span>
            </div>
          </div>
        )}
      </div>
      <MiniPlayer />
      <Lightbox />
    </div>
  )
}
