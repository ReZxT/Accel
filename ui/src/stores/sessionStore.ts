import { create } from 'zustand'
import type { Session, SessionId } from '../types'

const SESSIONS: Session[] = [
  { id: 'standard', label: 'Standard', icon: 'MessageSquare' },
  { id: 'coding', label: 'Coding', icon: 'Code' },
  { id: 'architecture', label: 'Architecture', icon: 'LayoutGrid' },
  { id: 'study', label: 'Study', icon: 'BookOpen' },
  { id: 'music', label: 'Music', icon: 'Music' },
  { id: 'news', label: 'News', icon: 'Newspaper' },
  { id: 'career', label: 'Career', icon: 'Briefcase' },
]

interface SessionStore {
  sessions: Session[]
  activeSession: SessionId
  switchSession: (id: SessionId) => void
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessions: SESSIONS,
  activeSession: (localStorage.getItem('accel_active_session') as SessionId) || 'standard',
  switchSession: (id) => {
    localStorage.setItem('accel_active_session', id)
    window.history.replaceState(null, '', `#${id}`)
    set({ activeSession: id })
  },
}))
