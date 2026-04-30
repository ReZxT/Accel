import { apiFetch } from './client'

interface VoiceStatus {
  enabled: boolean
}

export async function getVoiceStatus(): Promise<boolean> {
  const data = await apiFetch<VoiceStatus>('/voice/status')
  return data.enabled
}

export async function toggleVoice(enabled: boolean): Promise<boolean> {
  const data = await apiFetch<VoiceStatus>(
    `/voice/toggle?enabled=${enabled}`,
    { method: 'POST' },
  )
  return data.enabled
}
