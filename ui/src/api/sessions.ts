import { apiFetch } from './client'
import type { Message } from '../types'

interface SessionResponse {
  messages: Message[]
}

export async function loadSession(sessionId: string): Promise<Message[]> {
  const data = await apiFetch<SessionResponse>(
    `/session?session_id=${sessionId}&t=${Date.now()}`
  )
  return data.messages ?? []
}

export async function saveSession(sessionId: string, messages: Message[]): Promise<void> {
  const normalized = messages.map((m) =>
    m.role === 'bot' ? { ...m, role: 'assistant' as const } : m,
  )
  await apiFetch('/session', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, messages: normalized }),
  })
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch(`/session?session_id=${sessionId}`, {
    method: 'DELETE',
    timeout: 5000,
  })
}
