import { useEffect } from 'react'
import LeftNav from './LeftNav'
import RightPanel from './RightPanel'
import { useUIStore } from '../../stores/uiStore'

interface Props {
  children: React.ReactNode
}

export default function AppShell({ children }: Props) {
  const closePanel = useUIStore((s) => s.closePanel)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closePanel])

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary overflow-hidden">
      <LeftNav />
      <main className="flex-1 flex flex-col min-w-0">{children}</main>
      <RightPanel />
    </div>
  )
}
