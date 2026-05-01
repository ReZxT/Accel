import { useUIStore } from '../../stores/uiStore'
import { isElectron } from '../../api/electron'
import SessionList from '../sessions/SessionList'

export default function LeftNav() {
  const collapsed = useUIStore((s) => s.leftNavCollapsed)
  const toggleLeftNav = useUIStore((s) => s.toggleLeftNav)
  const openOverlay = useUIStore((s) => s.openOverlay)
  const activeView = useUIStore((s) => s.activeView)
  const setActiveView = useUIStore((s) => s.setActiveView)

  return (
    <nav
      className={`flex flex-col bg-surface border-r border-border h-full transition-[width] duration-200 ${
        collapsed ? 'w-16' : 'w-52'
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={toggleLeftNav}
        className="flex items-center justify-center h-12 text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
        title={collapsed ? 'Expand' : 'Collapse'}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${collapsed ? 'rotate-180' : ''}`}
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto px-2">
        <SessionList collapsed={collapsed} />
      </div>

      {/* Bottom controls */}
      <div className="flex flex-col gap-1 p-2 border-t border-border">
        {isElectron() && (
          <button
            onClick={() => setActiveView(activeView === 'services' ? 'chat' : 'services')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors cursor-pointer ${
              activeView === 'services'
                ? 'text-accent bg-accent-soft'
                : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
            }`}
            title="Services"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
              <line x1="6" y1="6" x2="6.01" y2="6" />
              <line x1="6" y1="18" x2="6.01" y2="18" />
            </svg>
            {!collapsed && <span className="text-sm">Services</span>}
          </button>
        )}
        <button
          onClick={() => openOverlay('settings')}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors cursor-pointer"
          title="Settings"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          {!collapsed && <span className="text-sm">Settings</span>}
        </button>
      </div>
    </nav>
  )
}
