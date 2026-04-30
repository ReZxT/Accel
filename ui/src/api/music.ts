import { apiFetch } from './client'
import type { NowPlaying } from '../types'

export async function getNowPlaying(): Promise<NowPlaying | null> {
  try {
    const data = await apiFetch<NowPlaying>('/music/now_playing', {
      timeout: 4000,
    })
    data.source = 'feishin'
    return data
  } catch {
    return null
  }
}

export async function playerControl(
  action: string,
  value: number = 0,
): Promise<void> {
  await apiFetch(`/music/control?action=${action}&value=${value}`, {
    method: 'POST',
  })
}
