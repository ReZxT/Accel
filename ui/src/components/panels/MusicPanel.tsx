import { useEffect, useRef } from 'react'
import { usePlayerStore } from '../../stores/playerStore'

function formatTime(secs: number) {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function MusicPanel() {
  const nowPlaying = usePlayerStore((s) => s.nowPlaying)
  const queue = usePlayerStore((s) => s.queue)
  const queueIndex = usePlayerStore((s) => s.queueIndex)
  const fetchNowPlaying = usePlayerStore((s) => s.fetchNowPlaying)
  const playPause = usePlayerStore((s) => s.playPause)
  const next = usePlayerStore((s) => s.next)
  const previous = usePlayerStore((s) => s.previous)
  const seek = usePlayerStore((s) => s.seek)
  const setAudioElement = usePlayerStore((s) => s.setAudioElement)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (audioRef.current) setAudioElement(audioRef.current)
  }, [setAudioElement])

  useEffect(() => {
    fetchNowPlaying()
    const id = setInterval(fetchNowPlaying, 3000)
    return () => clearInterval(id)
  }, [fetchNowPlaying])

  const np = nowPlaying
  const progress = np ? np.position / Math.max(np.length, 1) : 0

  return (
    <div className="flex flex-col h-full">
      <audio ref={audioRef} className="hidden" />

      {/* Art + info */}
      <div className="flex flex-col items-center gap-4 p-6">
        {np?.art_url ? (
          <img
            src={np.art_url}
            alt={np.title}
            className="w-48 h-48 rounded-lg object-cover shadow-lg"
          />
        ) : (
          <div className="w-48 h-48 rounded-lg bg-surface-hover flex items-center justify-center">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-tertiary">
              <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
            </svg>
          </div>
        )}

        <div className="text-center">
          <div className="text-sm font-medium text-text-primary truncate max-w-[280px]">
            {np?.title ?? 'Nothing playing'}
          </div>
          <div className="text-xs text-text-secondary mt-0.5">
            {np?.artist ?? '—'}{np?.album ? ` · ${np.album}` : ''}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-6">
        <div
          className="w-full h-1 bg-border rounded-full cursor-pointer"
          onClick={(e) => {
            if (!np) return
            const rect = e.currentTarget.getBoundingClientRect()
            const ratio = (e.clientX - rect.left) / rect.width
            seek(ratio * np.length)
          }}
        >
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-text-tertiary mt-1">
          <span>{np ? formatTime(np.position) : '0:00'}</span>
          <span>{np ? formatTime(np.length) : '0:00'}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-6 py-4">
        <button onClick={previous} className="text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="19 20 9 12 19 4 19 20" /><line x1="5" y1="19" x2="5" y2="5" />
          </svg>
        </button>
        <button
          onClick={playPause}
          className="w-10 h-10 rounded-full bg-accent flex items-center justify-center hover:bg-violet-500 transition-colors cursor-pointer"
        >
          {np?.status === 'playing' ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-white">
              <rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-white">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          )}
        </button>
        <button onClick={next} className="text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="5 4 15 12 5 20 5 4" /><line x1="19" y1="5" x2="19" y2="19" />
          </svg>
        </button>
      </div>

      {/* Queue */}
      {queue.length > 0 && (
        <div className="flex-1 overflow-y-auto border-t border-border">
          <div className="px-4 py-2 text-xs text-text-tertiary font-medium uppercase tracking-wider">Queue</div>
          {queue.map((track, i) => (
            <button
              key={track.id}
              onClick={() => usePlayerStore.getState().loadQueue(queue, i)}
              className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors cursor-pointer ${
                i === queueIndex
                  ? 'text-accent bg-accent-soft'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              }`}
            >
              <span className="text-xs w-5 text-center text-text-tertiary">{i + 1}</span>
              <div className="min-w-0">
                <div className="text-xs font-medium truncate">{track.title}</div>
                <div className="text-xs text-text-tertiary truncate">{track.artist}</div>
              </div>
              <span className="ml-auto text-xs text-text-tertiary flex-shrink-0">{formatTime(track.duration)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
