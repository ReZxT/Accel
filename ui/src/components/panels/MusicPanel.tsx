import { useEffect, useState } from 'react'
import { usePlayerStore } from '../../stores/playerStore'
import { getPlaylists, getPlaylistTracks, getLibrary, getRandomSongs } from '../../api/music'
import type { Track } from '../../types'

function formatTime(secs: number) {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

type View = 'player' | 'playlists' | 'playlist' | 'search'

interface Playlist {
  id: string
  name: string
  songCount: number
}

export default function MusicPanel() {
  const nowPlaying = usePlayerStore((s) => s.nowPlaying)
  const queue = usePlayerStore((s) => s.queue)
  const queueIndex = usePlayerStore((s) => s.queueIndex)
  const isPlaying = usePlayerStore((s) => s.isPlaying)
  const fetchNowPlaying = usePlayerStore((s) => s.fetchNowPlaying)
  const playPause = usePlayerStore((s) => s.playPause)
  const next = usePlayerStore((s) => s.next)
  const previous = usePlayerStore((s) => s.previous)
  const seek = usePlayerStore((s) => s.seek)
  const [view, setView] = useState<View>('player')
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [viewTracks, setViewTracks] = useState<Track[]>([])
  const [viewTitle, setViewTitle] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Track[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (queue.length === 0) {
      fetchNowPlaying()
      const id = setInterval(fetchNowPlaying, 3000)
      return () => clearInterval(id)
    }
  }, [fetchNowPlaying, queue.length])

  const loadPlaylists = async () => {
    setView('playlists')
    setLoading(true)
    try {
      const pls = await getPlaylists()
      setPlaylists(pls)
    } catch {}
    setLoading(false)
  }

  const loadPlaylist = async (id: string) => {
    setLoading(true)
    try {
      const data = await getPlaylistTracks(id)
      setViewTracks(data.tracks)
      setViewTitle(data.name)
      setView('playlist')
    } catch {}
    setLoading(false)
  }

  const loadRandom = async () => {
    setLoading(true)
    try {
      const tracks = await getRandomSongs(50)
      setViewTracks(tracks)
      setViewTitle('Random Mix')
      setView('playlist')
    } catch {}
    setLoading(false)
  }

  const doSearch = async () => {
    if (!searchQuery.trim()) return
    setLoading(true)
    try {
      const tracks = await getLibrary(searchQuery, 0, 50)
      setSearchResults(tracks)
      setView('search')
    } catch {}
    setLoading(false)
  }

  const playAll = (tracks: Track[], index = 0) => {
    usePlayerStore.getState().loadQueue(tracks, index)
    setView('player')
  }

  const np = nowPlaying
  const progress = np ? np.position / Math.max(np.length, 1) : 0

  return (
    <div className="flex flex-col h-full">

      {/* Nav bar */}
      <div className="flex items-center border-b border-border px-2 py-1.5 gap-1 flex-shrink-0">
        <NavBtn active={view === 'player'} onClick={() => setView('player')} label="Now Playing" />
        <NavBtn active={view === 'playlists'} onClick={loadPlaylists} label="Playlists" />
        <NavBtn active={false} onClick={loadRandom} label="Random" />
        <div className="flex-1" />
        <form onSubmit={(e) => { e.preventDefault(); doSearch() }} className="flex gap-1">
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            className="text-xs bg-black/20 border border-border rounded px-2 py-1 w-28 focus:w-40 transition-all outline-none focus:border-accent text-text-primary placeholder:text-text-tertiary"
          />
        </form>
      </div>

      {loading && <div className="text-center text-xs text-text-tertiary py-4">Loading...</div>}

      {/* Player view */}
      {view === 'player' && !loading && (
        <>
          <div className="flex flex-col items-center gap-3 p-5">
            {np?.art_url ? (
              <img src={np.art_url} alt={np.title} className="w-40 h-40 rounded-lg object-cover shadow-lg" />
            ) : (
              <div className="w-40 h-40 rounded-lg bg-surface-hover flex items-center justify-center">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-text-tertiary">
                  <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
                </svg>
              </div>
            )}
            <div className="text-center">
              <div className="text-sm font-medium text-text-primary truncate max-w-[260px]">{np?.title ?? 'Nothing playing'}</div>
              <div className="text-xs text-text-secondary mt-0.5">{np?.artist ?? '—'}{np?.album ? ` · ${np.album}` : ''}</div>
            </div>
          </div>

          <div className="px-5">
            <div className="w-full h-1 bg-border rounded-full cursor-pointer" onClick={(e) => {
              if (!np) return
              const rect = e.currentTarget.getBoundingClientRect()
              seek((e.clientX - rect.left) / rect.width * np.length)
            }}>
              <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${progress * 100}%` }} />
            </div>
            <div className="flex justify-between text-xs text-text-tertiary mt-1">
              <span>{np ? formatTime(np.position) : '0:00'}</span>
              <span>{np ? formatTime(np.length) : '0:00'}</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 py-3">
            <CtrlBtn onClick={previous}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="19 20 9 12 19 4 19 20" /><line x1="5" y1="19" x2="5" y2="5" /></svg>
            </CtrlBtn>
            <button onClick={playPause} className="w-10 h-10 rounded-full bg-accent flex items-center justify-center hover:bg-violet-500 transition-colors cursor-pointer">
              {(isPlaying || np?.status === 'playing') ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-white"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-white"><polygon points="5 3 19 12 5 21 5 3" /></svg>
              )}
            </button>
            <CtrlBtn onClick={next}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 4 15 12 5 20 5 4" /><line x1="19" y1="5" x2="19" y2="19" /></svg>
            </CtrlBtn>
          </div>

          {queue.length > 0 && (
            <TrackList
              tracks={queue}
              activeIndex={queueIndex}
              title="Queue"
              onPlay={(i) => usePlayerStore.getState().loadQueue(queue, i)}
            />
          )}
        </>
      )}

      {/* Playlists view */}
      {view === 'playlists' && !loading && (
        <div className="flex-1 overflow-y-auto">
          <div className="px-3 py-2 text-xs text-text-tertiary font-medium uppercase tracking-wider">Playlists</div>
          {playlists.map((pl) => (
            <button
              key={pl.id}
              onClick={() => loadPlaylist(pl.id)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/5 transition-colors cursor-pointer"
            >
              <div className="w-8 h-8 rounded bg-accent/15 flex items-center justify-center flex-shrink-0">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
                  <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-sm text-text-primary truncate">{pl.name}</div>
                <div className="text-xs text-text-tertiary">{pl.songCount} tracks</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Playlist detail / search results */}
      {(view === 'playlist' || view === 'search') && !loading && (
        <>
          <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
            <button onClick={() => view === 'playlist' ? loadPlaylists() : setView('player')} className="text-text-tertiary hover:text-text-primary cursor-pointer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
            </button>
            <span className="text-sm font-medium text-text-primary truncate">{view === 'search' ? `Search: "${searchQuery}"` : viewTitle}</span>
            <div className="flex-1" />
            {(view === 'playlist' ? viewTracks : searchResults).length > 0 && (
              <button
                onClick={() => playAll(view === 'playlist' ? viewTracks : searchResults)}
                className="text-xs px-2 py-1 rounded bg-accent/15 text-accent hover:bg-accent/25 transition-colors cursor-pointer"
              >
                Play all
              </button>
            )}
          </div>
          <TrackList
            tracks={view === 'playlist' ? viewTracks : searchResults}
            onPlay={(i) => playAll(view === 'playlist' ? viewTracks : searchResults, i)}
          />
        </>
      )}
    </div>
  )
}

function NavBtn({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2 py-1 rounded transition-colors cursor-pointer ${active ? 'bg-accent/15 text-accent' : 'text-text-tertiary hover:text-text-primary'}`}
    >
      {label}
    </button>
  )
}

function CtrlBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className="text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
      {children}
    </button>
  )
}

function TrackList({ tracks, title, activeIndex, onPlay }: { tracks: Track[]; title?: string; activeIndex?: number; onPlay: (i: number) => void }) {
  return (
    <div className="flex-1 overflow-y-auto border-t border-border">
      {title && <div className="px-3 py-2 text-xs text-text-tertiary font-medium uppercase tracking-wider">{title}</div>}
      {tracks.map((track, i) => (
        <button
          key={`${track.id}-${i}`}
          onClick={() => onPlay(i)}
          className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors cursor-pointer ${
            i === activeIndex ? 'text-accent bg-accent-soft' : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
          }`}
        >
          {track.art_url ? (
            <img src={track.art_url} className="w-8 h-8 rounded object-cover flex-shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded bg-surface-hover flex-shrink-0" />
          )}
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium truncate">{track.title}</div>
            <div className="text-xs text-text-tertiary truncate">{track.artist}</div>
          </div>
          <span className="text-xs text-text-tertiary flex-shrink-0">{formatTime(track.duration)}</span>
        </button>
      ))}
      {tracks.length === 0 && <div className="text-center text-xs text-text-tertiary py-4">No tracks</div>}
    </div>
  )
}
