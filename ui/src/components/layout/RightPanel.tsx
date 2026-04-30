import { useUIStore } from '../../stores/uiStore'
import ImagePreview from '../panels/ImagePreview'

export default function RightPanel() {
  const open = useUIStore((s) => s.rightPanelOpen)
  const panelType = useUIStore((s) => s.rightPanelType)
  const panelData = useUIStore((s) => s.rightPanelData)
  const closePanel = useUIStore((s) => s.closePanel)

  if (!open) return null

  const renderContent = () => {
    switch (panelType) {
      case 'image':
        return <ImagePreview src={panelData as string} />
      case 'canvas':
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            Canvas — coming soon
          </div>
        )
      case 'music':
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            Music player — coming soon
          </div>
        )
      default:
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            No content
          </div>
        )
    }
  }

  return (
    <div className="w-[40%] max-w-[600px] bg-surface border-l border-border flex flex-col h-screen">
      <div className="flex items-center justify-between px-4 h-12 border-b border-border">
        <span className="text-sm font-medium text-text-secondary capitalize">
          {panelType ?? 'Panel'}
        </span>
        <button
          onClick={closePanel}
          className="text-text-tertiary hover:text-text-primary transition-colors p-1"
          title="Close (Esc)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      {renderContent()}
    </div>
  )
}
