import { isElectron } from '../../api/electron'
import { electronWindow } from '../../api/electron'

export default function TitleBar() {
  if (!isElectron()) return null

  return (
    <div
      className="flex items-center justify-between h-9 bg-surface border-b border-border px-3 select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <span className="text-xs font-semibold text-text-tertiary">Accel</span>
      <div className="flex gap-1" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <button
          onClick={electronWindow.minimize}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-surface-hover text-text-tertiary hover:text-text-primary transition-colors"
        >
          <svg width="10" height="1" viewBox="0 0 10 1"><rect width="10" height="1" fill="currentColor" /></svg>
        </button>
        <button
          onClick={electronWindow.toggleMaximize}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-surface-hover text-text-tertiary hover:text-text-primary transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1"><rect x="0.5" y="0.5" width="9" height="9" /></svg>
        </button>
        <button
          onClick={electronWindow.close}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-error/20 text-text-tertiary hover:text-error transition-colors"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.5"><line x1="1" y1="1" x2="9" y2="9" /><line x1="9" y1="1" x2="1" y2="9" /></svg>
        </button>
      </div>
    </div>
  )
}
