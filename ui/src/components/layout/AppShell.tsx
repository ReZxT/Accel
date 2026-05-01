import { useEffect, useRef, useState, useCallback } from 'react'
import LeftNav from './LeftNav'
import RightPanel from './RightPanel'
import TitleBar from './TitleBar'
import { useUIStore } from '../../stores/uiStore'
import type { MessageImage, MessageFile } from '../../types'

const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
const LANGUAGE_MAP: Record<string, string> = {
  ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
  py: 'python', rs: 'rust', go: 'go', cpp: 'cpp', c: 'c', cs: 'csharp',
  java: 'java', rb: 'ruby', sh: 'bash', md: 'markdown', json: 'json',
  yaml: 'yaml', yml: 'yaml', toml: 'toml', html: 'html', css: 'css',
}

interface Props {
  children: React.ReactNode
}

export default function AppShell({ children }: Props) {
  const closePanel = useUIStore((s) => s.closePanel)
  const addPendingAttachments = useUIStore((s) => s.addPendingAttachments)
  const [dragging, setDragging] = useState(false)
  const dragCounter = useRef(0)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closePanel])

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
    </div>
  )
}
