# Accel UI Redesign — React Migration

**Date:** 2026-04-28
**Status:** Approved

## Goal

Replace the monolithic vanilla JS/CSS UI (`index.html`, `blob_ui.js`, `blob_ui.css`) with a React-based command center UI. Dual purpose: modernize the frontend to scale with Accel's roadmap (initiative layer, sensory extensions, identity coherence, task queues) and learn React + Tailwind CSS + TypeScript through building a real system.

## Stack

| Tool | Version | Purpose |
|------|---------|---------|
| Vite | latest | Build tool, dev server, HMR |
| React | 18 | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | v4 | Utility-first styling |
| Zustand | latest | Lightweight state management |
| marked | latest | Markdown rendering |
| tldraw | 2.4.0 | Canvas (architecture session) |
| pdf.js | 3.x | PDF attachment rendering |

No router, no form library, no animation library. Add when needed.

## Layout: Three-Column Command Center

```
+----------+-------------------------------+---------------------+
|          |                               |                     |
| Left Nav |         Center (Chat)         |    Right Panel      |
| (~64px   |                               |    (Adaptive)       |
| collapsed|  Message stream               |                     |
| ~200px   |  Tool activity inline         |  Canvas / Music /   |
| expanded)|  Thinking blocks              |  Image preview /    |
|          |                               |  File preview       |
| Sessions |                               |                     |
| Voice    |                               |  Hidden by default  |
| Status   |  +------------------------+   |  Slides in when     |
|          |  | Input bar + attachments|   |  content triggers   |
|          |  +------------------------+   |  it. Closeable.     |
+----------+-------------------------------+---------------------+
```

- **Left nav:** session buttons with icons, system controls at bottom (voice toggle, settings, memory inspector trigger). Collapsible — icons only when collapsed.
- **Center:** chat message stream, always visible, takes remaining space. Input bar pinned to bottom. Message content constrained to ~720-800px readable width, centered within the area.
- **Right panel:** 0px when hidden, 40% width when open (capped at 600px). Triggered by: image click, architecture session (canvas), music session (player), file preview. Closeable with X or Escape.

Desktop only. No mobile breakpoints — Android app planned separately.

## Visual Design Language

**Inspiration:** Linear (linear.app) layout and panel structure + Vercel (vercel.com) typography contrast and sharpness.

### Colors

- **Background:** near-black `#0a0a0a` to `#0e0e0e`, neutral (not warm, not blue-tinted)
- **Surfaces:** `#141414` for raised panels (left nav, right panel), `#1a1a1a` for cards/interactive elements
- **Borders:** `rgba(255,255,255,0.06)` where used — separation primarily through shade, not borders
- **Accent:** purple `#8b5cf6` for primary actions (send button, active session, interactive highlights)
- **Text:** near-white for primary, muted gray for secondary/tertiary
- **Semantic:** green for success/connected, red for errors, amber for warnings/approvals, blue for tool calls

### Typography

- **UI/body:** system sans-serif stack (Inter if available), 14px base, 12px for small labels
- **Code/data:** monospace (`JetBrains Mono` or `Geist Mono`) for tool names, timestamps, code blocks, status labels, arguments/output
- Dual-font approach is intentional — gives the developer-tool identity (Vercel's approach)

### Message Stream

- No bubbles. Full-width rows.
- Minimal left-side role indicator (small colored dot or subtle icon)
- User vs AI distinguished by slight background shift
- Compact vertical rhythm

### Tool/Thinking/Approval Cards

- Inset with `#141414` background
- Thin colored left border (2px): blue for tool calls, green for results, amber for approvals, purple for thinking
- Collapsible, monospace for arguments/output

### General

- **Corners:** 6px for cards, 8px for panels (Linear's approach)
- **Spacing:** 12-16px gaps, 8-12px internal padding. Dense but breathable.
- **Animations:** near zero. Fade-in for messages (150ms), slide for right panel (200ms). No decorative motion.
- **Scrollbar:** thin, custom styled, near-invisible until hovered.

## Component Architecture

### Layout

- `AppShell` — root layout, manages three-column flex
- `LeftNav` — session list, system controls, collapse toggle
- `MainContent` — wraps message stream + input bar
- `RightPanel` — adaptive content viewer, slides in/out

### Chat

- `MessageStream` — scrollable message list, auto-scroll
- `MessageItem` — single message row (role indicator, content, metadata, copy)
- `ThinkingBlock` — collapsible reasoning display
- `ToolCard` — tool call + result, collapsible, colored left border
- `ApprovalCard` — pending/resolved approval with approve/deny
- `InputBar` — textarea, send button, attachment button, previews
- `AttachmentPreview` — thumbnail strip for pending images/files

### Panels (right side)

- `CanvasPanel` — tldraw integration (architecture session)
- `MusicPlayer` — now playing, progress, controls, queue
- `ImagePreview` — fullscreen/panel image viewer
- `FilePreview` — code/text viewer

### Overlays

- `MemoryInspector` — popover showing personality, context state, recalled memories, profile
- `SettingsDialog` — tool approval settings, voice toggle, knowledge base management
- `CommandPalette` — future: quick actions via keyboard shortcut

## State Management (Zustand)

Four stores, each responsible for a clear domain:

### chatStore
- `messages[]` — full chat history for active session
- `isLoading` — streaming in progress
- `streamingText` / `streamingThinking` — accumulated during SSE
- `send(text, images, files)` — POST to `/chat`, start SSE stream
- `cancel()` — abort controller + POST `/cancel`
- `clear()` — clear messages + DELETE `/session`

### sessionStore
- `activeSession` — current session ID
- `sessions[]` — list of available sessions
- `switchSession(id)` — save current, load new, trigger session-specific features
- Persists to localStorage as fallback, syncs with `/session` endpoint

### uiStore
- `leftNavCollapsed` — boolean
- `rightPanel` — `{ open: boolean, type: 'canvas' | 'music' | 'image' | 'file' | null, data: any }`
- `overlays` — which overlays are open (settings, memory inspector)
- `openPanel(type, data)` / `closePanel()`

### playerStore
- `nowPlaying` — current track info (title, artist, album, position, duration, art)
- `source` — `'browser' | 'feishin'`
- `queue[]` — in-browser playback queue
- `play()` / `pause()` / `next()` / `previous()` / `seek()`
- Polls `/music/now_playing` when music session active

## Custom Hooks

- `useSSE(url, payload)` — manages SSE streaming connection, dispatches chunk types to appropriate stores
- `useNowPlaying()` — polling interval for music player state
- `useVoice()` — voice toggle status and control

## Data Flow

### No backend changes. Same FastAPI endpoints.

- **Chat:** `InputBar` → `chatStore.send()` → POST `/chat` → `useSSE` reads stream → chunks dispatched to `chatStore` (text, thinking, tool, approval) and `playerStore` (play_queue) and `uiStore` (canvas_command)
- **Sessions:** `sessionStore` loads/saves via `/session` endpoint. LocalStorage as offline fallback.
- **Approvals:** `ApprovalCard` renders inline during streaming. Approve/deny → POST `/approve/{id}`.
- **Music:** `playerStore` handles in-browser audio + Feishin via `/music/*` endpoints.
- **Right panel:** actions dispatch to `uiStore.openPanel()` → `RightPanel` renders appropriate component.

### Principle: stores are the single source of truth. Components read from stores. Actions go through store methods. No direct DOM manipulation.

## Project Structure

```
bootstrap/
  ui/                          # New React app
    src/
      components/
        layout/                # AppShell, LeftNav, RightPanel
        chat/                  # MessageStream, MessageItem, ToolCard, ApprovalCard, InputBar
        sessions/              # SessionList, SessionButton
        panels/                # CanvasPanel, MusicPlayer, ImagePreview, FilePreview
        overlays/              # MemoryInspector, SettingsDialog
      stores/                  # chatStore, sessionStore, uiStore, playerStore
      hooks/                   # useSSE, useNowPlaying, useVoice
      api/                     # chat.ts, sessions.ts, tools.ts
      types/                   # Message, Session, ToolCall, SSEChunk, etc.
      App.tsx
      main.tsx
      index.css                # Tailwind directives + minimal global styles
    index.html
    vite.config.ts
    tailwind.config.ts
    tsconfig.json
    package.json
  index.html                   # Old UI (kept until migration complete)
  blob_ui.js                   # Old UI
  blob_ui.css                  # Old UI
```

## Development Workflow

- Vite dev server on port 5173 during development
- Vite proxies API calls (`/chat`, `/session`, `/music/*`, etc.) to `localhost:8100`
- Old UI remains functional at port 80 (nginx) throughout migration
- When ready: `npm run build` → `ui/dist/` → nginx serves new UI
- Cutover is a nginx config change, instantly reversible

## Migration Strategy

Build incrementally. Each phase produces a working UI:

1. **Scaffold** — Vite + React + TS + Tailwind + Zustand. AppShell with three zones rendering placeholder content.
2. **Chat core** — MessageStream, MessageItem, InputBar. SSE streaming works. Can send/receive messages.
3. **Session management** — SessionList, session switching, history load/save.
4. **Tool activity** — ToolCard, ApprovalCard, ThinkingBlock rendering inline.
5. **Attachments** — image/file/PDF attachment, previews, drag-drop, paste.
6. **Right panel** — adaptive panel with image preview, canvas, music player.
7. **Overlays** — SettingsDialog, MemoryInspector, knowledge base management.
8. **Polish** — animations, keyboard shortcuts, command palette, edge cases.

Each phase is usable on its own. No big-bang switchover.

## Learning Goals

This project teaches through building:
- React component composition, props, children
- TypeScript interfaces and type narrowing
- Tailwind utility classes, responsive design thinking, custom theme
- Zustand store patterns, selectors, actions
- Custom hooks for side effects (SSE, polling, audio)
- Vite build tooling and dev workflow
