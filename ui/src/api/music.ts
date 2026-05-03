import { apiFetch } from './client'
import type { NowPlaying, Track } from '../types'

export async function getNowPlaying(): Promise<NowPlaying | null> {
  try {
    const data = await apiFetch<NowPlaying>('/music/now_playing', { timeout: 4000 })
    data.source = 'feishin'
    return data
  } catch {
    return null
  }
}

export async function playerControl(action: string, value: number = 0): Promise<void> {
  await apiFetch(`/music/control?action=${action}&value=${value}`, { method: 'POST' })
}

interface Playlist {
  id: string
  name: string
  songCount: number
  duration: number
}

export async function getPlaylists(): Promise<Playlist[]> {
  const data = await apiFetch<{ playlists: Playlist[] }>('/music/playlists')
  return data.playlists
}

export async function getPlaylistTracks(id: string): Promise<{ name: string; tracks: Track[] }> {
  return apiFetch(`/music/playlist/${id}`)
}

export async function getLibrary(query: string = '', offset = 0, count = 50): Promise<Track[]> {
  const data = await apiFetch<{ tracks: Track[] }>(`/music/library?query=${encodeURIComponent(query)}&offset=${offset}&count=${count}`)
  return data.tracks
}

export async function getRandomSongs(count = 50): Promise<Track[]> {
  const data = await apiFetch<{ tracks: Track[] }>(`/music/random?count=${count}`)
  return data.tracks
}
