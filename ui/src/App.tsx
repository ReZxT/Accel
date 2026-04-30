import { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import MessageStream from './components/chat/MessageStream'
import InputBar from './components/chat/InputBar'
import SettingsDialog from './components/overlays/SettingsDialog'
import { useChatStore } from './stores/chatStore'
import { useSessionStore } from './stores/sessionStore'
import { useUIStore } from './stores/uiStore'

export default function App() {
  const activeSession = useSessionStore((s) => s.activeSession)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const openPanel = useUIStore((s) => s.openPanel)
  const closePanel = useUIStore((s) => s.closePanel)

  useEffect(() => {
    loadHistory(activeSession)

    if (activeSession === 'architecture') {
      openPanel('canvas')
    } else if (activeSession === 'music') {
      openPanel('music')
    } else {
      closePanel()
    }
  }, [activeSession, loadHistory, openPanel, closePanel])

  useEffect(() => {
    const hash = window.location.hash.slice(1)
    if (hash) {
      const sessions = useSessionStore.getState().sessions
      if (sessions.some((s) => s.id === hash)) {
        useSessionStore.getState().switchSession(hash as any)
      }
    }
  }, [])

  return (
    <AppShell>
      <MessageStream />
      <InputBar />
      <SettingsDialog />
    </AppShell>
  )
}
