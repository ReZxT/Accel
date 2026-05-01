import { useEffect, useCallback } from 'react'
import { useUIStore } from '../../stores/uiStore'
import type { PanelMode } from '../../types'
import MusicPanel from '../panels/MusicPanel'
import CanvasPanel from '../panels/CanvasPanel'
import NotesPanel from '../panels/NotesPanel'
import FilePanel from '../panels/FilePanel'
import Tooltip from '../ui/Tooltip'

const TABS: { mode: PanelMode; label: string; icon: React.ReactNode }[] = [
  {
    mode: 'music',
    label: 'Music',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
      </svg>
    ),
  },
  {
    mode: 'canvas',
    label: 'Canvas',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 19l7-7 3 3-7 7-3-3z" /><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" /><path d="M2 2l7.586 7.586" /><circle cx="11" cy="11" r="2" />
      </svg>
    ),
  },
  {
    mode: 'notes',
    label: 'Notes',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    mode: 'file',
    label: 'File',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" />
      </svg>
    ),
  },
]

export default function RightPanel() {
  const panelOpen = useUIStore((s) => s.panelOpen)
  const panelMode = useUIStore((s) => s.panelMode)
  const panelPayload = useUIStore((s) => s.panelPayload)
  const openPanelMode = useUIStore((s) => s.openPanelMode)
  const togglePanel = useUIStore((s) => s.togglePanel)
  const closePanel = useUIStore((s) => s.closePanel)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') closePanel()
  }, [closePanel])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const renderContent = () => {
    switch (panelMode) {
      case 'music': return <MusicPanel />
      case 'canvas': return <CanvasPanel />
      case 'notes': return <NotesPanel path={panelPayload?.path} />
      case 'file': return <FilePanel path={panelPayload?.path} content={panelPayload?.content} />
    }
  }

  return (
    <div
      className={`flex flex-col bg-surface border-l border-border h-full transition-[width] duration-200 ${
        panelOpen ? 'w-[40%] max-w-[600px]' : 'w-10'
      }`}
    >
      {/* Tab bar — always visible */}
      <div className={`flex ${panelOpen ? 'flex-row border-b border-border' : 'flex-col'} items-center`}>
        {/* Toggle button */}
        <Tooltip text={panelOpen ? 'Close panel' : 'Open panel'} side={panelOpen ? 'top' : 'right'}>
          <button
            onClick={togglePanel}
            className="flex items-center justify-center w-10 h-10 flex-shrink-0 text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
          >
            <svg
              width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              className={`transition-transform ${panelOpen ? 'rotate-0' : 'rotate-180'}`}
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </Tooltip>

        {/* Mode tabs */}
        {TABS.map(({ mode, label, icon }) => (
          <Tooltip key={mode} text={label} side={panelOpen ? 'top' : 'right'} disabled={panelOpen}>
            <button
              onClick={() => openPanelMode(mode)}
              className={`flex items-center gap-2 px-3 h-10 text-sm transition-colors cursor-pointer ${
                panelOpen && panelMode === mode
                  ? 'text-accent border-b-2 border-accent'
                  : 'text-text-tertiary hover:text-text-primary'
              } ${!panelOpen ? 'w-10 justify-center' : ''}`}
            >
              {icon}
              {panelOpen && <span>{label}</span>}
            </button>
          </Tooltip>
        ))}
      </div>

      {/* Content */}
      {panelOpen && (
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          {renderContent()}
        </div>
      )}
    </div>
  )
}
