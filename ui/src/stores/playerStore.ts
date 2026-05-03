import { create } from 'zustand'
import type { NowPlaying, Track } from '../types'
import { getNowPlaying, playerControl } from '../api/music'

interface PlayerStore {
  nowPlaying: NowPlaying | null
  queue: Track[]
  queueIndex: number
  audioElement: HTMLAudioElement | null
  isPlaying: boolean

  setAudioElement: (el: HTMLAudioElement) => void
  fetchNowPlaying: () => Promise<void>
  loadQueue: (tracks: Track[], index?: number) => void
  playPause: () => void
  next: () => void
  previous: () => void
  seek: (seconds: number) => void
  updatePosition: (position: number) => void
}

export const usePlayerStore = create<PlayerStore>((set, get) => ({
  nowPlaying: null,
  queue: [],
  queueIndex: 0,
  audioElement: null,
  isPlaying: false,

  setAudioElement: (el) => {
    if (get().audioElement === el) return
    el.addEventListener('timeupdate', () => {
      const { nowPlaying } = get()
      if (nowPlaying && nowPlaying.source === 'browser') {
        set({ nowPlaying: { ...nowPlaying, position: el.currentTime } })
      }
    })
    el.addEventListener('play', () => set({ isPlaying: true }))
    el.addEventListener('pause', () => set({ isPlaying: false }))
    el.addEventListener('ended', () => {
      const { queue, queueIndex } = get()
      if (queueIndex < queue.length - 1) {
        get().loadQueue(queue, queueIndex + 1)
      } else {
        set({ isPlaying: false })
      }
    })
    set({ audioElement: el })
  },

  fetchNowPlaying: async () => {
    const { queue } = get()
    if (queue.length > 0) return
    const np = await getNowPlaying()
    if (np) set({ nowPlaying: np })
  },

  loadQueue: (tracks, index = 0) => {
    const { audioElement } = get()
    if (!audioElement || !tracks.length) return
    set({ queue: tracks, queueIndex: index })
    const track = tracks[index]
    audioElement.src = track.stream_url
    audioElement.play().catch(() => {})
    set({
      nowPlaying: {
        source: 'browser',
        status: 'playing',
        title: track.title,
        artist: track.artist,
        album: track.album,
        length: track.duration,
        position: 0,
        art_url: track.art_url,
      },
    })
  },

  playPause: () => {
    const { audioElement, queue } = get()
    if (queue.length > 0 && audioElement) {
      if (audioElement.paused) {
        audioElement.play()
      } else {
        audioElement.pause()
      }
    } else {
      playerControl('play_pause').then(() => {
        setTimeout(() => get().fetchNowPlaying(), 300)
      })
    }
  },

  next: () => {
    const { queue, queueIndex } = get()
    if (queue.length > 0 && queueIndex < queue.length - 1) {
      get().loadQueue(queue, queueIndex + 1)
    } else {
      playerControl('next').then(() => {
        setTimeout(() => get().fetchNowPlaying(), 300)
      })
    }
  },

  previous: () => {
    const { audioElement, queue, queueIndex } = get()
    if (queue.length > 0) {
      if (audioElement && audioElement.currentTime > 3) {
        audioElement.currentTime = 0
      } else if (queueIndex > 0) {
        get().loadQueue(queue, queueIndex - 1)
      }
    } else {
      playerControl('previous').then(() => {
        setTimeout(() => get().fetchNowPlaying(), 300)
      })
    }
  },

  seek: (seconds) => {
    const { audioElement, queue } = get()
    if (queue.length > 0 && audioElement) {
      audioElement.currentTime = seconds
    } else {
      playerControl('seek', seconds)
    }
  },

  updatePosition: (position) =>
    set((s) =>
      s.nowPlaying ? { nowPlaying: { ...s.nowPlaying, position } } : {},
    ),
}))
