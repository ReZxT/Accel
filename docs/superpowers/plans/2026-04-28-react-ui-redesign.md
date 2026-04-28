# Accel React UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vanilla JS/CSS UI with a React + TypeScript + Tailwind CSS command center UI, building incrementally so each task produces working software.

**Architecture:** Three-column layout (left nav, center chat, adaptive right panel) built as isolated React components. Zustand stores manage all state (chat, sessions, UI, player). The React app lives in `ui/` and talks to the same FastAPI backend — no backend changes. Vite dev server proxies API calls to `:8100` during development.

**Tech Stack:** Vite, React 18, TypeScript, Tailwind CSS v4, Zustand, marked (markdown), tldraw 2.4.0, pdf.js 3.x

**Spec:** `docs/superpowers/specs/2026-04-28-react-ui-redesign-design.md`

---

## File Map

```
ui/
  index.html                           # Vite entry HTML
  vite.config.ts                       # Vite config with API proxy
  tsconfig.json                        # TypeScript config
  package.json                         # Dependencies
  src/
    main.tsx                           # React root mount
    App.tsx                            # AppShell — three-column layout
    index.css                          # Tailwind directives + global styles

    types/
      index.ts                         # All shared types: Message, Session, SSEChunk, ToolCall, etc.

    api/
      client.ts                        # Shared fetch helpers (base URL, error handling)
      sessions.ts                      # Session CRUD (load, save, delete, poll)
      tools.ts                         # Tool settings GET/PUT
      voice.ts                         # Voice toggle/status
      music.ts                         # Now playing, player control

    stores/
      sessionStore.ts                  # Active session, session list, switching
      chatStore.ts                     # Messages, loading, streaming, send/cancel/clear
      uiStore.ts                       # Left nav collapse, right panel, overlays
      playerStore.ts                   # Now playing, queue, browser audio, controls

    hooks/
      useSSE.ts                        # SSE streaming hook — reads response, dispatches to stores
      useNowPlaying.ts                 # Music player polling hook
      useVoice.ts                      # Voice toggle status hook

    components/
      layout/
        AppShell.tsx                   # Root three-column flex layout
        LeftNav.tsx                    # Session list + system controls sidebar
        RightPanel.tsx                 # Adaptive content panel (slides in/out)

      chat/
        MessageStream.tsx              # Scrollable message list with auto-scroll
        MessageItem.tsx                # Single message row (role dot, content, meta, copy)
        InputBar.tsx                   # Textarea + send + attach + preview strip
        AttachmentPreview.tsx          # Thumbnails/cards for pending files/images

      chat/blocks/
        ThinkingBlock.tsx              # Collapsible thinking/reasoning display
        ToolCallBlock.tsx              # Tool call display (name + args, collapsible)
        ToolResultBlock.tsx            # Tool result display (output or screenshot)
        ApprovalBlock.tsx              # Pending/resolved approval with buttons

      sessions/
        SessionList.tsx                # Maps sessions to buttons
        SessionButton.tsx              # Individual session button with icon + label

      panels/
        ImagePreview.tsx               # Image viewer in right panel
        MusicPlayer.tsx                # Now playing + controls + queue
        CanvasPanel.tsx                # tldraw wrapper

      overlays/
        SettingsDialog.tsx             # Tool approval + voice toggle + KB management
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `ui/package.json`
- Create: `ui/vite.config.ts`
- Create: `ui/tsconfig.json`
- Create: `ui/index.html`
- Create: `ui/src/main.tsx`
- Create: `ui/src/App.tsx`
- Create: `ui/src/index.css`
- Create: `ui/.gitignore`

- [ ] **Step 1: Initialize the Vite project**

```bash
cd /home/rezxt/bootstrap && mkdir ui && cd ui
npm create vite@latest . -- --template react-ts
```

Select "Ignore files and continue" if prompted about non-empty directory.

- [ ] **Step 2: Install dependencies**

```bash
cd /home/rezxt/bootstrap/ui
npm install zustand marked
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Vite with API proxy and Tailwind plugin**

Replace `ui/vite.config.ts` with:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/chat': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/cancel': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/status': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/approve': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/settings': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/voice': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/music': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/canvas': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/session': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/profile': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/ingest': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/kb': {
        target: 'http://localhost:9200',
        changeOrigin: true,
      },
      '/navidrome': {
        target: 'http://localhost:4533',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/navidrome/, ''),
      },
    },
  },
})
```

- [ ] **Step 4: Set up Tailwind CSS v4 with custom theme**

Replace `ui/src/index.css` with:

```css
@import "tailwindcss";

@theme {
  --color-bg-primary: #0a0a0a;
  --color-bg-secondary: #0e0e0e;
  --color-surface: #141414;
  --color-surface-hover: #1a1a1a;
  --color-border: rgba(255, 255, 255, 0.06);
  --color-border-hi: rgba(255, 255, 255, 0.12);

  --color-accent: #8b5cf6;
  --color-accent-soft: rgba(139, 92, 246, 0.15);
  --color-accent-glow: rgba(139, 92, 246, 0.35);

  --color-text-primary: rgba(255, 255, 255, 0.92);
  --color-text-secondary: rgba(255, 255, 255, 0.55);
  --color-text-tertiary: rgba(255, 255, 255, 0.30);

  --color-success: #22c55e;
  --color-error: #f87171;
  --color-warning: #fbbf24;
  --color-info: #3b82f6;

  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Geist Mono', ui-monospace, monospace;
}

body {
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

/* Thin scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.15); }
```

- [ ] **Step 5: Write the entry HTML**

Replace `ui/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Accel</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write the React entry point**

Replace `ui/src/main.tsx` with:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 7: Write the placeholder App shell**

Replace `ui/src/App.tsx` with:

```tsx
export default function App() {
  return (
    <div className="flex h-screen bg-bg-primary text-text-primary">
      {/* Left Nav */}
      <nav className="w-16 bg-surface flex flex-col items-center py-4 border-r border-border">
        <span className="text-xs text-text-tertiary">Nav</span>
      </nav>

      {/* Center — Chat */}
      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
            <p className="text-sm text-text-secondary">React UI scaffold working.</p>
          </div>
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 8: Add .gitignore for ui/**

Create `ui/.gitignore`:

```
node_modules
dist
```

- [ ] **Step 9: Verify the dev server starts**

```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

Open `http://localhost:5173` in a browser. You should see "Accel" in purple and "React UI scaffold working." on a dark background. The three-column flex should be visible — a narrow dark nav on the left, content filling the rest.

- [ ] **Step 10: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/
git commit -m "feat(ui): scaffold Vite + React + TypeScript + Tailwind project"
```

---

## Task 2: Type Definitions

**Files:**
- Create: `ui/src/types/index.ts`

- [ ] **Step 1: Define all shared types**

Create `ui/src/types/index.ts`:

```ts
export type MessageRole = 'user' | 'bot' | 'assistant'

export interface MessageImage {
  base64: string
  name: string
  type: string
  dataUrl?: string
}

export interface MessageFile {
  content: string
  name: string
  language: string
  size?: number
}

export interface Message {
  role: MessageRole
  content: string
  timestamp: string
  images?: MessageImage[]
  files?: MessageFile[]
  thoughts?: string
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
}

export interface ToolResult {
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export interface ApprovalRequest {
  request_id: string
  tool: string
  args: Record<string, unknown>
}

export type SSEChunk =
  | { type: 'text'; text: string }
  | { type: 'thinking'; text: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; output: string; image?: string; mime_type?: string }
  | { type: 'approval_request'; request_id: string; tool: string; args: Record<string, unknown> }
  | { type: 'tool_denied'; tool: string }
  | { type: 'canvas_command'; command: string; data: Record<string, unknown> }
  | { type: 'play_queue'; tracks: Track[] }
  | { type: 'route'; route: Record<string, unknown> }
  | { type: 'error'; text: string }

export interface Track {
  id: string
  title: string
  artist: string
  album: string
  duration: number
  stream_url: string
  art_url: string
}

export interface NowPlaying {
  source: 'browser' | 'feishin'
  status: 'playing' | 'paused' | 'stopped'
  title: string
  artist: string
  album: string
  length: number
  position: number
  art_url: string
}

export type SessionId = 'standard' | 'coding' | 'architecture' | 'study' | 'music'

export interface Session {
  id: SessionId
  label: string
  icon: string
}

export type PanelType = 'canvas' | 'music' | 'image' | 'file' | null

export interface RightPanelState {
  open: boolean
  type: PanelType
  data?: unknown
}

export type OverlayType = 'settings' | 'memory' | null

export interface ToolSetting {
  label: string
  desc: string
  irreversible: boolean
}

export type ToolPolicy = 'require' | 'auto'

export interface StreamingToolCall {
  id: string
  tool: string
  args: Record<string, unknown>
}

export interface StreamingToolResult {
  id: string
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export interface StreamingApproval {
  request_id: string
  tool: string
  args: Record<string, unknown>
  resolved?: boolean
  approved?: boolean
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/rezxt/bootstrap/ui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/types/
git commit -m "feat(ui): add TypeScript type definitions for all data models"
```

---

## Task 3: API Client Layer

**Files:**
- Create: `ui/src/api/client.ts`
- Create: `ui/src/api/sessions.ts`
- Create: `ui/src/api/tools.ts`
- Create: `ui/src/api/voice.ts`
- Create: `ui/src/api/music.ts`

- [ ] **Step 1: Create shared fetch client**

Create `ui/src/api/client.ts`:

```ts
const BASE = ''

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { timeout?: number },
): Promise<T> {
  const { timeout = 8000, ...fetchInit } = init ?? {}
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  const res = await fetch(`${BASE}${path}`, {
    ...fetchInit,
    signal: controller.signal,
  })

  clearTimeout(id)

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${text.slice(0, 300)}`)
  }

  return res.json()
}
```

- [ ] **Step 2: Create sessions API**

Create `ui/src/api/sessions.ts`:

```ts
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
```

- [ ] **Step 3: Create tools API**

Create `ui/src/api/tools.ts`:

```ts
import { apiFetch } from './client'
import type { ToolPolicy } from '../types'

interface ToolSettingsResponse {
  tool_settings: Record<string, ToolPolicy>
}

export async function getToolSettings(): Promise<Record<string, ToolPolicy>> {
  const data = await apiFetch<ToolSettingsResponse>('/settings/tools', {
    timeout: 5000,
  })
  return data.tool_settings ?? {}
}

export async function updateToolSettings(
  settings: Record<string, ToolPolicy>,
): Promise<void> {
  await apiFetch('/settings/tools', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_settings: settings }),
  })
}

export async function resolveApproval(
  requestId: string,
  approved: boolean,
): Promise<void> {
  await apiFetch(`/approve/${requestId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved }),
  })
}
```

- [ ] **Step 4: Create voice API**

Create `ui/src/api/voice.ts`:

```ts
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
```

- [ ] **Step 5: Create music API**

Create `ui/src/api/music.ts`:

```ts
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
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd /home/rezxt/bootstrap/ui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/api/
git commit -m "feat(ui): add API client layer for sessions, tools, voice, music"
```

---

## Task 4: Zustand Stores

**Files:**
- Create: `ui/src/stores/sessionStore.ts`
- Create: `ui/src/stores/uiStore.ts`
- Create: `ui/src/stores/chatStore.ts`
- Create: `ui/src/stores/playerStore.ts`

- [ ] **Step 1: Create session store**

Create `ui/src/stores/sessionStore.ts`:

```ts
import { create } from 'zustand'
import type { Session, SessionId } from '../types'

const SESSIONS: Session[] = [
  { id: 'standard', label: 'Standard', icon: 'MessageSquare' },
  { id: 'coding', label: 'Coding', icon: 'Code' },
  { id: 'architecture', label: 'Architecture', icon: 'LayoutGrid' },
  { id: 'study', label: 'Study', icon: 'BookOpen' },
  { id: 'music', label: 'Music', icon: 'Music' },
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
```

- [ ] **Step 2: Create UI store**

Create `ui/src/stores/uiStore.ts`:

```ts
import { create } from 'zustand'
import type { PanelType, OverlayType } from '../types'

interface UIStore {
  leftNavCollapsed: boolean
  toggleLeftNav: () => void

  rightPanelOpen: boolean
  rightPanelType: PanelType
  rightPanelData: unknown
  openPanel: (type: PanelType, data?: unknown) => void
  closePanel: () => void

  activeOverlay: OverlayType
  openOverlay: (type: OverlayType) => void
  closeOverlay: () => void
}

export const useUIStore = create<UIStore>((set) => ({
  leftNavCollapsed: false,
  toggleLeftNav: () => set((s) => ({ leftNavCollapsed: !s.leftNavCollapsed })),

  rightPanelOpen: false,
  rightPanelType: null,
  rightPanelData: undefined,
  openPanel: (type, data) =>
    set({ rightPanelOpen: true, rightPanelType: type, rightPanelData: data }),
  closePanel: () =>
    set({ rightPanelOpen: false, rightPanelType: null, rightPanelData: undefined }),

  activeOverlay: null,
  openOverlay: (type) => set({ activeOverlay: type }),
  closeOverlay: () => set({ activeOverlay: null }),
}))
```

- [ ] **Step 3: Create chat store**

Create `ui/src/stores/chatStore.ts`:

```ts
import { create } from 'zustand'
import type {
  Message,
  MessageImage,
  MessageFile,
  StreamingToolCall,
  StreamingToolResult,
  StreamingApproval,
} from '../types'
import { loadSession, saveSession, deleteSession } from '../api/sessions'

interface ChatStore {
  messages: Message[]
  isLoading: boolean
  streamingText: string
  streamingThinking: string
  streamingTools: StreamingToolCall[]
  streamingResults: StreamingToolResult[]
  streamingApprovals: StreamingApproval[]
  abortController: AbortController | null

  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  appendStreamText: (text: string) => void
  appendStreamThinking: (text: string) => void
  addStreamToolCall: (tc: StreamingToolCall) => void
  addStreamToolResult: (tr: StreamingToolResult) => void
  addStreamApproval: (a: StreamingApproval) => void
  resolveApproval: (requestId: string, approved: boolean) => void

  startLoading: (controller: AbortController) => void
  finishStreaming: (sessionId: string) => void
  cancelStream: (sessionId: string) => void

  loadHistory: (sessionId: string) => Promise<void>
  clearChat: (sessionId: string) => Promise<void>
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isLoading: false,
  streamingText: '',
  streamingThinking: '',
  streamingTools: [],
  streamingResults: [],
  streamingApprovals: [],
  abortController: null,

  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  appendStreamText: (text) =>
    set((s) => ({ streamingText: s.streamingText + text })),
  appendStreamThinking: (text) =>
    set((s) => ({ streamingThinking: s.streamingThinking + text })),
  addStreamToolCall: (tc) =>
    set((s) => ({ streamingTools: [...s.streamingTools, tc] })),
  addStreamToolResult: (tr) =>
    set((s) => ({ streamingResults: [...s.streamingResults, tr] })),
  addStreamApproval: (a) =>
    set((s) => ({ streamingApprovals: [...s.streamingApprovals, a] })),
  resolveApproval: (requestId, approved) =>
    set((s) => ({
      streamingApprovals: s.streamingApprovals.map((a) =>
        a.request_id === requestId ? { ...a, resolved: true, approved } : a,
      ),
    })),

  startLoading: (controller) =>
    set({
      isLoading: true,
      streamingText: '',
      streamingThinking: '',
      streamingTools: [],
      streamingResults: [],
      streamingApprovals: [],
      abortController: controller,
    }),

  finishStreaming: (sessionId) => {
    const { streamingText, streamingThinking, messages } = get()
    if (streamingText.trim()) {
      const botMsg: Message = {
        role: 'bot',
        content: streamingText,
        timestamp: new Date().toISOString(),
        thoughts: streamingThinking || undefined,
      }
      const updated = [...messages, botMsg]
      set({
        messages: updated,
        isLoading: false,
        abortController: null,
        streamingText: '',
        streamingThinking: '',
        streamingTools: [],
        streamingResults: [],
        streamingApprovals: [],
      })
      localStorage.setItem(`accel_chat_${sessionId}`, JSON.stringify(updated))
      saveSession(sessionId, updated).catch(() => {})
    } else {
      set({
        isLoading: false,
        abortController: null,
        streamingText: '',
        streamingThinking: '',
        streamingTools: [],
        streamingResults: [],
        streamingApprovals: [],
      })
    }
  },

  cancelStream: (sessionId) => {
    const { abortController } = get()
    if (abortController) abortController.abort()
    fetch(`/cancel?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'POST',
    }).catch(() => {})
    get().finishStreaming(sessionId)
  },

  loadHistory: async (sessionId) => {
    try {
      const messages = await loadSession(sessionId)
      const normalized = messages.map((m) =>
        m.role === ('assistant' as string)
          ? { ...m, role: 'bot' as const, content: (m.content ?? '').replace(/<think>[\s\S]*?<\/think>/gi, '').trim() }
          : m,
      )
      set({ messages: normalized })
      localStorage.setItem(`accel_chat_${sessionId}`, JSON.stringify(normalized))
    } catch {
      const saved = localStorage.getItem(`accel_chat_${sessionId}`)
      if (saved) {
        try {
          set({ messages: JSON.parse(saved) })
        } catch { /* corrupt data */ }
      }
    }
  },

  clearChat: async (sessionId) => {
    set({ messages: [] })
    localStorage.removeItem(`accel_chat_${sessionId}`)
    try {
      await deleteSession(sessionId)
    } catch { /* ignore */ }
  },
}))
```

- [ ] **Step 4: Create player store**

Create `ui/src/stores/playerStore.ts`:

```ts
import { create } from 'zustand'
import type { NowPlaying, Track } from '../types'
import { getNowPlaying, playerControl } from '../api/music'

interface PlayerStore {
  nowPlaying: NowPlaying | null
  queue: Track[]
  queueIndex: number
  audioElement: HTMLAudioElement | null

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

  setAudioElement: (el) => set({ audioElement: el }),

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
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd /home/rezxt/bootstrap/ui && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/stores/
git commit -m "feat(ui): add Zustand stores for session, chat, UI, and player state"
```

---

## Task 5: Layout Components (AppShell, LeftNav, RightPanel)

**Files:**
- Create: `ui/src/components/layout/AppShell.tsx`
- Create: `ui/src/components/layout/LeftNav.tsx`
- Create: `ui/src/components/layout/RightPanel.tsx`
- Modify: `ui/src/App.tsx`

- [ ] **Step 1: Create LeftNav component**

Create `ui/src/components/layout/LeftNav.tsx`:

```tsx
import { useSessionStore } from '../../stores/sessionStore'
import { useUIStore } from '../../stores/uiStore'
import SessionList from '../sessions/SessionList'

export default function LeftNav() {
  const collapsed = useUIStore((s) => s.leftNavCollapsed)
  const toggleLeftNav = useUIStore((s) => s.toggleLeftNav)
  const openOverlay = useUIStore((s) => s.openOverlay)

  return (
    <nav
      className={`flex flex-col bg-surface border-r border-border h-screen transition-[width] duration-200 ${
        collapsed ? 'w-16' : 'w-52'
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={toggleLeftNav}
        className="flex items-center justify-center h-12 text-text-tertiary hover:text-text-primary transition-colors"
        title={collapsed ? 'Expand' : 'Collapse'}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${collapsed ? 'rotate-180' : ''}`}
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto px-2">
        <SessionList collapsed={collapsed} />
      </div>

      {/* Bottom controls */}
      <div className="flex flex-col gap-1 p-2 border-t border-border">
        <button
          onClick={() => openOverlay('settings')}
          className="flex items-center gap-3 px-3 py-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
          title="Settings"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          {!collapsed && <span className="text-sm">Settings</span>}
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Create SessionList and SessionButton components**

Create `ui/src/components/sessions/SessionList.tsx`:

```tsx
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
```

Create `ui/src/components/sessions/SessionButton.tsx`:

```tsx
import type { Session } from '../../types'

const ICONS: Record<string, JSX.Element> = {
  MessageSquare: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  Code: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
    </svg>
  ),
  LayoutGrid: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    </svg>
  ),
  BookOpen: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  Music: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
    </svg>
  ),
}

interface Props {
  session: Session
  active: boolean
  collapsed: boolean
  onClick: () => void
}

export default function SessionButton({ session, active, collapsed, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      title={session.label}
      className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
        active
          ? 'bg-accent-soft text-text-primary'
          : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
      }`}
    >
      <span className="flex-shrink-0">{ICONS[session.icon]}</span>
      {!collapsed && <span className="text-sm truncate">{session.label}</span>}
    </button>
  )
}
```

- [ ] **Step 3: Create RightPanel component**

Create `ui/src/components/layout/RightPanel.tsx`:

```tsx
import { useUIStore } from '../../stores/uiStore'

export default function RightPanel() {
  const open = useUIStore((s) => s.rightPanelOpen)
  const panelType = useUIStore((s) => s.rightPanelType)
  const closePanel = useUIStore((s) => s.closePanel)

  if (!open) return null

  return (
    <div className="w-[40%] max-w-[600px] bg-surface border-l border-border flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 h-12 border-b border-border">
        <span className="text-sm font-medium text-text-secondary capitalize">
          {panelType ?? 'Panel'}
        </span>
        <button
          onClick={closePanel}
          className="text-text-tertiary hover:text-text-primary transition-colors p-1"
          title="Close (Esc)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Content — panels will be added in later tasks */}
      <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
        {panelType} panel
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create AppShell component**

Create `ui/src/components/layout/AppShell.tsx`:

```tsx
import { useEffect } from 'react'
import LeftNav from './LeftNav'
import RightPanel from './RightPanel'
import { useUIStore } from '../../stores/uiStore'

interface Props {
  children: React.ReactNode
}

export default function AppShell({ children }: Props) {
  const closePanel = useUIStore((s) => s.closePanel)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closePanel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closePanel])

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary overflow-hidden">
      <LeftNav />
      <main className="flex-1 flex flex-col min-w-0">{children}</main>
      <RightPanel />
    </div>
  )
}
```

- [ ] **Step 5: Update App.tsx to use AppShell**

Replace `ui/src/App.tsx` with:

```tsx
import AppShell from './components/layout/AppShell'

export default function App() {
  return (
    <AppShell>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
          <p className="text-sm text-text-secondary">
            Layout shell working. Chat goes here.
          </p>
        </div>
      </div>
    </AppShell>
  )
}
```

- [ ] **Step 6: Verify in browser**

```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

Open `http://localhost:5173`. You should see:
- Left nav with 5 session buttons (Standard, Coding, Architecture, Study, Music) and a settings button at the bottom
- Clicking a session highlights it in purple
- The collapse button shrinks the nav to icons-only
- Center shows placeholder text
- No right panel visible (it appears when triggered)

- [ ] **Step 7: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/components/ ui/src/App.tsx
git commit -m "feat(ui): add AppShell, LeftNav, RightPanel, SessionList layout"
```

---

## Task 6: Chat — InputBar Component

**Files:**
- Create: `ui/src/components/chat/InputBar.tsx`
- Modify: `ui/src/App.tsx`

- [ ] **Step 1: Create InputBar component**

Create `ui/src/components/chat/InputBar.tsx`:

```tsx
import { useState, useRef, useCallback } from 'react'
import { useChatStore } from '../../stores/chatStore'
import { useSessionStore } from '../../stores/sessionStore'

export default function InputBar() {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const isLoading = useChatStore((s) => s.isLoading)
  const cancelStream = useChatStore((s) => s.cancelStream)
  const activeSession = useSessionStore((s) => s.activeSession)

  const handleSend = useCallback(() => {
    if (isLoading) {
      cancelStream(activeSession)
      return
    }
    const trimmed = text.trim()
    if (!trimmed) return

    const { addMessage, startLoading, appendStreamText, appendStreamThinking, addStreamToolCall, addStreamToolResult, addStreamApproval, finishStreaming } = useChatStore.getState()

    const userMsg = {
      role: 'user' as const,
      content: trimmed,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMsg)
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const controller = new AbortController()
    startLoading(controller)

    const messages = useChatStore.getState().messages
    const payload = {
      chatInput: trimmed,
      chatHistory: messages.slice(-60).map((m) =>
        m.role === 'bot' ? { ...m, role: 'assistant' } : m,
      ),
      sessionId: activeSession,
    }

    fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buf = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop()!

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const raw = line.slice(6).trim()
            if (raw === '[DONE]') break
            try {
              const chunk = JSON.parse(raw)
              if (chunk.type === 'text') appendStreamText(chunk.text)
              else if (chunk.type === 'thinking') appendStreamThinking(chunk.text)
              else if (chunk.type === 'tool_call') {
                addStreamToolCall({ id: `tc_${Date.now()}`, tool: chunk.tool, args: chunk.args })
              } else if (chunk.type === 'tool_result') {
                addStreamToolResult({ id: `tr_${Date.now()}`, tool: chunk.tool, output: chunk.output, image: chunk.image, mime_type: chunk.mime_type })
              } else if (chunk.type === 'approval_request') {
                addStreamApproval({ request_id: chunk.request_id, tool: chunk.tool, args: chunk.args })
              }
            } catch { /* malformed chunk */ }
          }
        }
        finishStreaming(activeSession)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          addMessage({
            role: 'bot',
            content: `Error: ${err.message}`,
            timestamp: new Date().toISOString(),
          })
        }
        finishStreaming(activeSession)
      })
  }, [text, isLoading, activeSession, cancelStream])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 150) + 'px'
  }

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-end gap-3 bg-surface border border-border rounded-lg px-4 py-3 focus-within:border-border-hi transition-colors">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Message Accel..."
          rows={1}
          className="flex-1 bg-transparent text-text-primary text-sm outline-none resize-none max-h-[150px] leading-relaxed placeholder:text-text-tertiary"
        />
        <button
          onClick={handleSend}
          className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-colors ${
            isLoading
              ? 'bg-error text-white'
              : 'bg-accent text-white hover:brightness-110'
          }`}
          title={isLoading ? 'Cancel' : 'Send'}
        >
          {isLoading ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire InputBar into App.tsx**

Replace `ui/src/App.tsx` with:

```tsx
import AppShell from './components/layout/AppShell'
import InputBar from './components/chat/InputBar'

export default function App() {
  return (
    <AppShell>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
          <p className="text-sm text-text-secondary">Message stream goes here.</p>
        </div>
      </div>
      <InputBar />
    </AppShell>
  )
}
```

- [ ] **Step 3: Verify in browser**

```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

Open `http://localhost:5173`. You should see:
- Input bar at the bottom with a textarea and purple send button
- Typing text and pressing Enter sends it (check network tab for POST to `/chat`)
- The send button turns red with a stop icon while loading
- Shift+Enter creates a new line instead of sending
- Textarea auto-grows as you type

- [ ] **Step 4: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/components/chat/InputBar.tsx ui/src/App.tsx
git commit -m "feat(ui): add InputBar with SSE streaming and cancel support"
```

---

## Task 7: Chat — MessageStream and MessageItem

**Files:**
- Create: `ui/src/components/chat/MessageStream.tsx`
- Create: `ui/src/components/chat/MessageItem.tsx`
- Create: `ui/src/lib/format.ts`
- Modify: `ui/src/App.tsx`

- [ ] **Step 1: Create formatting utilities**

Create `ui/src/lib/format.ts`:

```ts
import { marked } from 'marked'

export function formatMarkdown(text: string): string {
  try {
    return marked.parse(text) as string
  } catch {
    return escapeHtml(text).replace(/\n/g, '<br>')
  }
}

export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

export function formatTimestamp(ts: string): string {
  if (!ts) return ''
  if (/^\d{2}:\d{2}$/.test(ts)) return ts
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts
  const now = new Date()
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (d.toDateString() === now.toDateString()) return time
  const sameYear = d.getFullYear() === now.getFullYear()
  const dateStr = d.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
  })
  return `${dateStr}, ${time}`
}
```

- [ ] **Step 2: Create MessageItem component**

Create `ui/src/components/chat/MessageItem.tsx`:

```tsx
import { useState, useCallback } from 'react'
import type { Message } from '../../types'
import { formatMarkdown, formatTimestamp } from '../../lib/format'

interface Props {
  message: Message
}

export default function MessageItem({ message }: Props) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [message.content])

  return (
    <div className={`px-4 py-3 ${isUser ? 'bg-white/[0.02]' : ''}`}>
      <div className="max-w-3xl mx-auto flex gap-3">
        {/* Role indicator */}
        <div className="flex-shrink-0 mt-1">
          <div
            className={`w-2 h-2 rounded-full ${
              isUser ? 'bg-accent' : 'bg-success'
            }`}
          />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div
            className="text-sm leading-relaxed prose-invert [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_a]:no-underline [&_a:hover]:text-blue-300 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
            dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
          />

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2 text-xs text-text-tertiary">
            <span>{formatTimestamp(message.timestamp)}</span>
            <button
              onClick={handleCopy}
              className="hover:text-text-secondary transition-colors"
              title="Copy"
            >
              {copied ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create streaming message display**

Create `ui/src/components/chat/MessageStream.tsx`:

```tsx
import { useRef, useEffect } from 'react'
import { useChatStore } from '../../stores/chatStore'
import MessageItem from './MessageItem'
import { formatMarkdown } from '../../lib/format'

export default function MessageStream() {
  const messages = useChatStore((s) => s.messages)
  const isLoading = useChatStore((s) => s.isLoading)
  const streamingText = useChatStore((s) => s.streamingText)
  const streamingThinking = useChatStore((s) => s.streamingThinking)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
          <p className="text-sm text-text-tertiary max-w-sm">
            Your second brain. Ask anything, build anything, remember everything.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.map((msg, i) => (
        <MessageItem key={`${msg.timestamp}-${i}`} message={msg} />
      ))}

      {/* Streaming message */}
      {isLoading && (
        <div className="px-4 py-3">
          <div className="max-w-3xl mx-auto flex gap-3">
            <div className="flex-shrink-0 mt-1">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
            </div>
            <div className="min-w-0 flex-1">
              {streamingThinking && (
                <div className="text-xs text-orange-400/80 italic border-l-2 border-orange-400/40 pl-2 mb-2">
                  Thinking...
                </div>
              )}
              {streamingText ? (
                <div
                  className="text-sm leading-relaxed [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(streamingText) }}
                />
              ) : (
                <div className="flex gap-1 py-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" />
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.15s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.3s]" />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 4: Wire MessageStream into App.tsx**

Replace `ui/src/App.tsx` with:

```tsx
import { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import MessageStream from './components/chat/MessageStream'
import InputBar from './components/chat/InputBar'
import { useChatStore } from './stores/chatStore'
import { useSessionStore } from './stores/sessionStore'

export default function App() {
  const activeSession = useSessionStore((s) => s.activeSession)
  const loadHistory = useChatStore((s) => s.loadHistory)

  useEffect(() => {
    loadHistory(activeSession)
  }, [activeSession, loadHistory])

  return (
    <AppShell>
      <MessageStream />
      <InputBar />
    </AppShell>
  )
}
```

- [ ] **Step 5: Verify in browser**

```bash
cd /home/rezxt/bootstrap/ui && npm run dev
```

Open `http://localhost:5173`. You should see:
- Welcome state when no messages exist
- Sending a message shows a user message row (purple dot, content, timestamp)
- AI response streams in with an orange pulsing dot, then finalizes with a green dot
- Messages have timestamps and copy buttons
- The message stream auto-scrolls as new content arrives
- Markdown renders correctly (bold, code blocks, lists, links)

- [ ] **Step 6: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/
git commit -m "feat(ui): add MessageStream, MessageItem, and markdown rendering"
```

---

## Task 8: Session Switching with History

**Files:**
- Modify: `ui/src/App.tsx`
- Modify: `ui/src/components/layout/LeftNav.tsx`

- [ ] **Step 1: Add session switch logic to App.tsx**

Replace `ui/src/App.tsx` with:

```tsx
import { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import MessageStream from './components/chat/MessageStream'
import InputBar from './components/chat/InputBar'
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

  // Hash routing on initial load
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
    </AppShell>
  )
}
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:5173`. Test:
- Click different sessions in the left nav — chat history loads for each
- Architecture session opens the right panel (shows "canvas panel" placeholder)
- Music session opens the right panel (shows "music panel" placeholder)
- Other sessions close the right panel
- URL hash updates when switching sessions
- Loading `http://localhost:5173/#music` goes directly to music session

- [ ] **Step 3: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/App.tsx
git commit -m "feat(ui): add session switching with history load and panel triggers"
```

---

## Task 9: Tool Activity Blocks (ToolCall, ToolResult, Approval, Thinking)

**Files:**
- Create: `ui/src/components/chat/blocks/ThinkingBlock.tsx`
- Create: `ui/src/components/chat/blocks/ToolCallBlock.tsx`
- Create: `ui/src/components/chat/blocks/ToolResultBlock.tsx`
- Create: `ui/src/components/chat/blocks/ApprovalBlock.tsx`
- Modify: `ui/src/components/chat/MessageStream.tsx`
- Modify: `ui/src/components/chat/MessageItem.tsx`

- [ ] **Step 1: Create ThinkingBlock**

Create `ui/src/components/chat/blocks/ThinkingBlock.tsx`:

```tsx
import { useState } from 'react'
import { escapeHtml } from '../../../lib/format'

interface Props {
  content: string
}

export default function ThinkingBlock({ content }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-md border border-accent/20 overflow-hidden mb-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 bg-accent/[0.06] text-xs font-medium text-text-secondary hover:bg-accent/10 transition-colors"
      >
        <span className="text-text-tertiary">Thoughts</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <div className="px-3 py-2 bg-black/25 border-t border-accent/10 text-xs text-text-secondary font-mono whitespace-pre-wrap max-h-[400px] overflow-y-auto leading-relaxed">
          {content}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create ToolCallBlock**

Create `ui/src/components/chat/blocks/ToolCallBlock.tsx`:

```tsx
import { useState } from 'react'
import { escapeHtml } from '../../../lib/format'

interface Props {
  tool: string
  args: Record<string, unknown>
}

export default function ToolCallBlock({ tool, args }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-md border-l-2 border-l-info bg-surface overflow-hidden mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-hover transition-colors"
      >
        <span className="font-mono font-semibold text-text-secondary">{tool}</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create ToolResultBlock**

Create `ui/src/components/chat/blocks/ToolResultBlock.tsx`:

```tsx
import { useState } from 'react'
import { useUIStore } from '../../../stores/uiStore'

interface Props {
  tool: string
  output: string
  image?: string
  mime_type?: string
}

export default function ToolResultBlock({ tool, output, image, mime_type }: Props) {
  const [open, setOpen] = useState(false)
  const openPanel = useUIStore((s) => s.openPanel)

  if (image) {
    const src = `data:${mime_type || 'image/png'};base64,${image}`
    return (
      <div className="rounded-md border-l-2 border-l-success bg-surface overflow-hidden mb-1">
        <div className="px-3 py-1.5 text-xs">
          <span className="font-mono font-semibold text-text-secondary">{tool}</span>
          <span className="text-text-tertiary ml-2">screenshot</span>
        </div>
        <img
          src={src}
          alt="Screenshot"
          className="max-w-full rounded-sm mx-3 mb-2 border border-border cursor-pointer hover:opacity-90 transition-opacity"
          onClick={() => openPanel('image', src)}
        />
      </div>
    )
  }

  const truncated = output.length > 2000 ? output.slice(0, 2000) + '\n... (truncated)' : output

  return (
    <div className="rounded-md border-l-2 border-l-success bg-surface overflow-hidden mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-hover transition-colors"
      >
        <span className="font-mono font-semibold text-text-secondary">{tool}</span>
        <span className="text-text-tertiary">result</span>
        <span className="ml-auto text-[10px] text-text-tertiary">
          {open ? 'Hide' : 'Show'}
        </span>
      </button>
      {open && (
        <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
          {truncated}
        </pre>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create ApprovalBlock**

Create `ui/src/components/chat/blocks/ApprovalBlock.tsx`:

```tsx
import { resolveApproval } from '../../../api/tools'
import { useChatStore } from '../../../stores/chatStore'
import type { StreamingApproval } from '../../../types'

interface Props {
  approval: StreamingApproval
}

export default function ApprovalBlock({ approval }: Props) {
  const resolve = useChatStore((s) => s.resolveApproval)

  const handleResolve = (approved: boolean) => {
    resolve(approval.request_id, approved)
    resolveApproval(approval.request_id, approved).catch(() => {})
  }

  if (approval.resolved) {
    return (
      <div
        className={`rounded-md border-l-2 px-3 py-1.5 text-xs font-semibold mb-1 ${
          approval.approved
            ? 'border-l-success bg-success/[0.06] text-success'
            : 'border-l-error bg-error/[0.06] text-error'
        }`}
      >
        {approval.approved ? 'Approved' : 'Denied'}: {approval.tool}
      </div>
    )
  }

  return (
    <div className="rounded-md border-l-2 border-l-warning bg-warning/[0.06] overflow-hidden mb-1">
      <div className="px-3 py-1.5 text-xs">
        <span className="font-mono font-semibold text-text-secondary">{approval.tool}</span>
        <span className="text-warning ml-2">requires approval</span>
      </div>
      <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto">
        {JSON.stringify(approval.args, null, 2)}
      </pre>
      <div className="flex gap-2 px-3 py-2 border-t border-border">
        <button
          onClick={() => handleResolve(true)}
          className="px-3 py-1 rounded text-xs font-semibold bg-success/20 text-success hover:bg-success/30 transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => handleResolve(false)}
          className="px-3 py-1 rounded text-xs font-semibold bg-error/20 text-error hover:bg-error/30 transition-colors"
        >
          Deny
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Add ThinkingBlock to MessageItem**

Replace the content of `ui/src/components/chat/MessageItem.tsx` — add the import and render thoughts:

```tsx
import { useState, useCallback } from 'react'
import type { Message } from '../../types'
import { formatMarkdown, formatTimestamp } from '../../lib/format'
import ThinkingBlock from './blocks/ThinkingBlock'

interface Props {
  message: Message
}

export default function MessageItem({ message }: Props) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [message.content])

  return (
    <div className={`px-4 py-3 ${isUser ? 'bg-white/[0.02]' : ''}`}>
      <div className="max-w-3xl mx-auto flex gap-3">
        <div className="flex-shrink-0 mt-1">
          <div
            className={`w-2 h-2 rounded-full ${
              isUser ? 'bg-accent' : 'bg-success'
            }`}
          />
        </div>
        <div className="min-w-0 flex-1">
          {message.thoughts && <ThinkingBlock content={message.thoughts} />}
          <div
            className="text-sm leading-relaxed [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_a]:no-underline [&_a:hover]:text-blue-300 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
            dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
          />
          <div className="flex items-center gap-3 mt-2 text-xs text-text-tertiary">
            <span>{formatTimestamp(message.timestamp)}</span>
            <button
              onClick={handleCopy}
              className="hover:text-text-secondary transition-colors"
              title="Copy"
            >
              {copied ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Add streaming tool blocks to MessageStream**

Replace `ui/src/components/chat/MessageStream.tsx` with:

```tsx
import { useRef, useEffect } from 'react'
import { useChatStore } from '../../stores/chatStore'
import MessageItem from './MessageItem'
import ToolCallBlock from './blocks/ToolCallBlock'
import ToolResultBlock from './blocks/ToolResultBlock'
import ApprovalBlock from './blocks/ApprovalBlock'
import { formatMarkdown } from '../../lib/format'

export default function MessageStream() {
  const messages = useChatStore((s) => s.messages)
  const isLoading = useChatStore((s) => s.isLoading)
  const streamingText = useChatStore((s) => s.streamingText)
  const streamingThinking = useChatStore((s) => s.streamingThinking)
  const streamingTools = useChatStore((s) => s.streamingTools)
  const streamingResults = useChatStore((s) => s.streamingResults)
  const streamingApprovals = useChatStore((s) => s.streamingApprovals)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText, streamingTools, streamingResults, streamingApprovals])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
          <p className="text-sm text-text-tertiary max-w-sm">
            Your second brain. Ask anything, build anything, remember everything.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.map((msg, i) => (
        <MessageItem key={`${msg.timestamp}-${i}`} message={msg} />
      ))}

      {isLoading && (
        <div className="px-4 py-3">
          <div className="max-w-3xl mx-auto flex gap-3">
            <div className="flex-shrink-0 mt-1">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
            </div>
            <div className="min-w-0 flex-1">
              {streamingThinking && (
                <div className="text-xs text-orange-400/80 italic border-l-2 border-orange-400/40 pl-2 mb-2">
                  Thinking...
                </div>
              )}

              {/* Tool activity */}
              {streamingTools.map((tc) => (
                <ToolCallBlock key={tc.id} tool={tc.tool} args={tc.args} />
              ))}
              {streamingResults.map((tr) => (
                <ToolResultBlock key={tr.id} tool={tr.tool} output={tr.output} image={tr.image} mime_type={tr.mime_type} />
              ))}
              {streamingApprovals.map((a) => (
                <ApprovalBlock key={a.request_id} approval={a} />
              ))}

              {streamingText ? (
                <div
                  className="text-sm leading-relaxed [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(streamingText) }}
                />
              ) : (
                !streamingTools.length && (
                  <div className="flex gap-1 py-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.15s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.3s]" />
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 7: Verify in browser**

Open `http://localhost:5173`. Test:
- Send a message that triggers tool use (e.g., "search the web for X")
- Tool call blocks appear with blue left border, collapsible
- Tool result blocks appear with green left border, collapsible
- Approval requests show amber block with Approve/Deny buttons
- Clicking Approve/Deny resolves the card and posts to `/approve/`
- Messages with thinking blocks show a collapsible "Thoughts" section
- Screenshots in tool results are clickable (will open right panel with image preview in a later task)

- [ ] **Step 8: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/
git commit -m "feat(ui): add tool call, result, approval, and thinking blocks"
```

---

## Task 10: Right Panel — Image Preview

**Files:**
- Create: `ui/src/components/panels/ImagePreview.tsx`
- Modify: `ui/src/components/layout/RightPanel.tsx`

- [ ] **Step 1: Create ImagePreview component**

Create `ui/src/components/panels/ImagePreview.tsx`:

```tsx
interface Props {
  src: string
}

export default function ImagePreview({ src }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
      <img
        src={src}
        alt="Preview"
        className="max-w-full max-h-full rounded-md object-contain"
      />
    </div>
  )
}
```

- [ ] **Step 2: Wire ImagePreview into RightPanel**

Replace `ui/src/components/layout/RightPanel.tsx` with:

```tsx
import { useUIStore } from '../../stores/uiStore'
import ImagePreview from '../panels/ImagePreview'

export default function RightPanel() {
  const open = useUIStore((s) => s.rightPanelOpen)
  const panelType = useUIStore((s) => s.rightPanelType)
  const panelData = useUIStore((s) => s.rightPanelData)
  const closePanel = useUIStore((s) => s.closePanel)

  if (!open) return null

  const renderContent = () => {
    switch (panelType) {
      case 'image':
        return <ImagePreview src={panelData as string} />
      case 'canvas':
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            Canvas — coming soon
          </div>
        )
      case 'music':
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            Music player — coming soon
          </div>
        )
      default:
        return (
          <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
            No content
          </div>
        )
    }
  }

  return (
    <div className="w-[40%] max-w-[600px] bg-surface border-l border-border flex flex-col h-screen">
      <div className="flex items-center justify-between px-4 h-12 border-b border-border">
        <span className="text-sm font-medium text-text-secondary capitalize">
          {panelType ?? 'Panel'}
        </span>
        <button
          onClick={closePanel}
          className="text-text-tertiary hover:text-text-primary transition-colors p-1"
          title="Close (Esc)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      {renderContent()}
    </div>
  )
}
```

- [ ] **Step 3: Verify in browser**

Test: trigger a screenshot tool result, click the screenshot image — the right panel should open showing the full image. Press Escape or click X to close.

- [ ] **Step 4: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/
git commit -m "feat(ui): add ImagePreview in right panel"
```

---

## Task 11: Settings Dialog

**Files:**
- Create: `ui/src/components/overlays/SettingsDialog.tsx`
- Modify: `ui/src/App.tsx`

- [ ] **Step 1: Create SettingsDialog component**

Create `ui/src/components/overlays/SettingsDialog.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { useUIStore } from '../../stores/uiStore'
import { useChatStore } from '../../stores/chatStore'
import { useSessionStore } from '../../stores/sessionStore'
import { getToolSettings, updateToolSettings } from '../../api/tools'
import { toggleVoice, getVoiceStatus } from '../../api/voice'
import type { ToolPolicy } from '../../types'

const TOOL_LABELS: Record<string, { desc: string; irreversible: boolean }> = {
  bash: { desc: 'Shell command execution', irreversible: true },
  write_file: { desc: 'Create or overwrite files', irreversible: true },
  edit_file: { desc: 'Edit existing files', irreversible: true },
  delete_file: { desc: 'Delete a file', irreversible: true },
  move_file: { desc: 'Move or rename a file', irreversible: true },
  read_file: { desc: 'Read file contents', irreversible: false },
  search_files: { desc: 'Search by name or content', irreversible: false },
  list_dir: { desc: 'List directory contents', irreversible: false },
  search_web: { desc: 'Web search via SearXNG', irreversible: false },
  fetch_url: { desc: 'Fetch and read a URL', irreversible: false },
  screenshot_url: { desc: 'Screenshot a web page', irreversible: false },
  calculate: { desc: 'Evaluate a math expression', irreversible: false },
  search_knowledge_base: { desc: 'Search ingested documents', irreversible: false },
  save_memory: { desc: 'Save to memory collection', irreversible: false },
  search_music: { desc: 'Search YouTube/SoundCloud', irreversible: false },
  download_music: { desc: 'Download audio to /mnt/WD/Music', irreversible: true },
}

export default function SettingsDialog() {
  const activeOverlay = useUIStore((s) => s.activeOverlay)
  const closeOverlay = useUIStore((s) => s.closeOverlay)
  const clearChat = useChatStore((s) => s.clearChat)
  const activeSession = useSessionStore((s) => s.activeSession)
  const [toolSettings, setToolSettings] = useState<Record<string, ToolPolicy>>({})
  const [voiceEnabled, setVoiceEnabled] = useState(false)

  useEffect(() => {
    if (activeOverlay === 'settings') {
      getToolSettings().then(setToolSettings).catch(() => {})
      getVoiceStatus().then(setVoiceEnabled).catch(() => {})
    }
  }, [activeOverlay])

  if (activeOverlay !== 'settings') return null

  const handleToolChange = (tool: string, policy: ToolPolicy) => {
    const updated = { ...toolSettings, [tool]: policy }
    setToolSettings(updated)
    updateToolSettings(updated).catch(() => {})
  }

  const handleVoiceToggle = () => {
    const next = !voiceEnabled
    setVoiceEnabled(next)
    toggleVoice(next).then(setVoiceEnabled).catch(() => setVoiceEnabled(!next))
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => e.target === e.currentTarget && closeOverlay()}
    >
      <div className="bg-bg-secondary border border-border rounded-lg w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold">Settings</h2>
          <button onClick={closeOverlay} className="text-text-tertiary hover:text-text-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {/* Voice toggle */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-secondary">Voice Mode</span>
            <button
              onClick={handleVoiceToggle}
              className={`w-9 h-5 rounded-full transition-colors relative ${
                voiceEnabled ? 'bg-accent' : 'bg-white/10'
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  voiceEnabled ? 'left-[18px]' : 'left-0.5'
                }`}
              />
            </button>
          </div>

          {/* Clear chat */}
          <button
            onClick={() => { clearChat(activeSession); closeOverlay() }}
            className="text-sm text-error hover:text-error/80 transition-colors"
          >
            Clear Chat
          </button>

          {/* Tool approval */}
          <div>
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              Tool Approval
            </h3>
            <div className="space-y-2">
              {Object.entries(TOOL_LABELS).map(([tool, info]) => {
                const policy = toolSettings[tool] || (info.irreversible ? 'require' : 'auto')
                return (
                  <div key={tool} className="flex items-center justify-between py-1">
                    <div>
                      <span className="text-sm font-mono font-semibold text-text-secondary">{tool}</span>
                      <span className="text-xs text-text-tertiary ml-2">{info.desc}</span>
                    </div>
                    <select
                      value={policy}
                      onChange={(e) => handleToolChange(tool, e.target.value as ToolPolicy)}
                      className="text-xs bg-surface border border-border rounded px-2 py-1 text-text-primary"
                    >
                      <option value="require">Require</option>
                      <option value="auto">Auto</option>
                    </select>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add SettingsDialog to App.tsx**

Add the import and render it alongside the other components:

```tsx
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
```

- [ ] **Step 3: Verify in browser**

Test: click the settings gear in the left nav. A modal should appear with:
- Voice toggle switch
- Clear Chat button
- Tool approval list with dropdowns
- Clicking outside the modal or X closes it

- [ ] **Step 4: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/src/
git commit -m "feat(ui): add SettingsDialog with voice toggle and tool approval"
```

---

## Task 12: Build & Nginx Integration

**Files:**
- Modify: `ui/vite.config.ts` (add build output config)
- Modify: `bootstrap/docker-compose.yml` (mount ui/dist)
- Modify: `bootstrap/nginx.conf` (serve from ui/dist)

- [ ] **Step 1: Build the React app**

```bash
cd /home/rezxt/bootstrap/ui && npm run build
```

Expected: output in `ui/dist/` with `index.html`, `assets/` folder containing `.js` and `.css` bundles.

```bash
ls ui/dist/
ls ui/dist/assets/
```

- [ ] **Step 2: Update docker-compose.yml to mount the new UI**

Add the `ui/dist` volume mounts to the nginx service. Replace the old file mounts:

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: bootstrap-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ui/dist:/usr/share/nginx/html:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always
```

- [ ] **Step 3: Rebuild nginx container**

```bash
cd /home/rezxt/bootstrap && docker compose up -d nginx
```

- [ ] **Step 4: Verify at port 80**

Open `http://localhost` in a browser. The new React UI should load — same experience as the Vite dev server but served through nginx.

- [ ] **Step 5: Commit**

```bash
cd /home/rezxt/bootstrap
git add ui/dist/ docker-compose.yml
git commit -m "feat(ui): build React app and serve via nginx"
```

Note: if you prefer not to commit `ui/dist/`, add it to `.gitignore` and run `npm run build` as a deploy step instead. Both approaches work — committing dist keeps it simple for now.
