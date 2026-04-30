import { useSessionStore } from '../../stores/sessionStore'
import SessionButton from './SessionButton'

interface Props {
  collapsed: boolean
}

export default function SessionList({ collapsed }: Props) {
  const sessions = useSessionStore((s) => s.sessions)
  const activeSession = useSessionStore((s) => s.activeSession)
  const switchSession = useSessionStore((s) => s.switchSession)

  return (
    <div className="flex flex-col gap-1">
      {sessions.map((session) => (
        <SessionButton
          key={session.id}
          session={session}
          active={session.id === activeSession}
          collapsed={collapsed}
          onClick={() => switchSession(session.id)}
        />
      ))}
    </div>
  )
}
