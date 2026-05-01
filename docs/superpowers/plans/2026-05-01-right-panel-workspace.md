# Right Panel Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the session-specific right panel with a global multi-mode workspace (Music, Canvas, Notes, File) that persists its active mode across sessions and can be opened/switched by the model via SSE events.

**Architecture:** The right panel becomes a standalone global workspace with a tab bar for switching modes. A new `panelMode` field in `uiStore` replaces the session-coupled `rightPanelType`. The backend emits a new `open_panel` SSE chunk type that the `InputBar` stream handler responds to by dispatching `openPanelMode()`. Notes mode adds a backend API route for browsing and reading/writing vault files at `/mnt/WD/The Ideas`.

**Tech Stack:** React 18, Zustand, TypeScript, Tailwind CSS, Python FastAPI, marked (markdown rendering, already used via `formatMarkdown`)

---

## File Structure

**Modified:**
- `ui/src/stores/uiStore.ts` — replace `rightPanelType`/`rightPanelData` with `panelMode: PanelMode`, `panelOpen: boolean`, `openPanelMode(mode, payload?)`, `togglePanel()`, `closePanel()`
- `ui/src/types/index.ts` — add `PanelMode` type, `OpenPanelPayload` interface, `open_panel` SSEChunk variant
- `ui/src/components/layout/RightPanel.tsx` — rewrite as tab bar + mode router; remove session coupling
- `ui/src/components/layout/AppShell.tsx` — remove `closePanel` on Escape (keep it in RightPanel)
- `ui/src/App.tsx` — remove `openPanel`/`closePanel` calls tied to `activeSession`
- `ui/src/components/chat/InputBar.tsx` — handle `open_panel` SSE chunk
- `bootstrap/api/notes.py` — new FastAPI router: `GET /notes/tree`, `GET /notes/file?path=`, `PUT /notes/file`
- `bootstrap/main.py` — register notes router
- `bootstrap/agents/chat_agent.py` — emit `open_panel` SSE chunk for `__type == "open_panel"` tool results

**Created:**
- `ui/src/components/panels/MusicPanel.tsx` — now-playing, queue, transport controls (moved from wherever music lives)
- `ui/src/components/panels/CanvasPanel.tsx` — tldraw canvas (extracted from current RightPanel `'canvas'` stub)
- `ui/src/components/panels/NotesPanel.tsx` — file tree sidebar + markdown viewer/editor
- `ui/src/components/panels/FilePanel.tsx` — generic file/image viewer

---

## Task 1: Extend types and uiStore

**Files:**
- Modify: `ui/src/types/index.ts`
- Modify: `ui/src/stores/uiStore.ts`

- [ ] **Step 1: Update `PanelType` → `PanelMode` and add `open_panel` SSE chunk in types**

Replace the `PanelType` type and add the new SSE chunk in `ui/src/types/index.ts`:

```typescript
// Replace:
// export type PanelType = 'canvas' | 'music' | 'image' | 'file' | null

export type PanelMode = 'music' | 'canvas' | 'notes' | 'file'

export interface OpenPanelPayload {
  path?: string      // for notes/file: vault-relative path to open
  content?: string   // for file: inline content if no path
}

// Add to the SSEChunk union (after the canvas_command variant):
// | { type: 'open_panel'; mode: PanelMode; payload?: OpenPanelPayload }
```

Full updated `SSEChunk` union in `ui/src/types/index.ts`:

```typescript
export type SSEChunk =
  | { type: 'text'; text: string }
  | { type: 'thinking'; text: string }
  | { type: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { type: 'tool_result'; tool: string; output: string; image?: string; mime_type?: string }
  | { type: 'approval_request'; request_id: string; tool: string; args: Record<string, unknown> }
  | { type: 'tool_denied'; tool: string }
  | { type: 'canvas_command'; command: string; data: Record<string, unknown> }
  | { type: 'open_panel'; mode: PanelMode; payload?: OpenPanelPayload }
  | { type: 'play_queue'; tracks: Track[] }
  | { type: 'route'; route: Record<string, unknown> }
  | { type: 'error'; text: string }
```

Also remove `PanelType` and `RightPanelState` from the file (they'll be replaced). Keep `OverlayType` as-is.

- [ ] **Step 2: Rewrite the relevant section of `uiStore.ts`**

Replace the `rightPanelOpen / rightPanelType / rightPanelData / openPanel / closePanel` block with:

```typescript
// in the UIStore interface:
panelOpen: boolean
panelMode: PanelMode
panelPayload: OpenPanelPayload | undefined
openPanelMode: (mode: PanelMode, payload?: OpenPanelPayload) => void
togglePanel: () => void
closePanel: () => void
```

Full updated `ui/src/stores/uiStore.ts`:

```typescript
import { create } from 'zustand'
import type { OverlayType, MessageImage, MessageFile, PanelMode, OpenPanelPayload } from '../types'

interface UIStore {
  leftNavCollapsed: boolean
  toggleLeftNav: () => void

  panelOpen: boolean
  panelMode: PanelMode
  panelPayload: OpenPanelPayload | undefined
  openPanelMode: (mode: PanelMode, payload?: OpenPanelPayload) => void
  togglePanel: () => void
  closePanel: () => void

  activeOverlay: OverlayType
  openOverlay: (type: OverlayType) => void
  closeOverlay: () => void

  activeView: 'chat' | 'services'
  setActiveView: (view: 'chat' | 'services') => void

  pendingImages: MessageImage[]
  pendingFiles: MessageFile[]
  addPendingAttachments: (images: MessageImage[], files: MessageFile[]) => void
  removeImage: (i: number) => void
  removeFile: (i: number) => void
  clearAttachments: () => void
}

export const useUIStore = create<UIStore>((set, get) => ({
  leftNavCollapsed: false,
  toggleLeftNav: () => set((s) => ({ leftNavCollapsed: !s.leftNavCollapsed })),

  panelOpen: false,
  panelMode: 'music',
  panelPayload: undefined,
  openPanelMode: (mode, payload) =>
    set({ panelOpen: true, panelMode: mode, panelPayload: payload }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  closePanel: () => set({ panelOpen: false, panelPayload: undefined }),

  activeOverlay: null,
  openOverlay: (type) => set({ activeOverlay: type }),
  closeOverlay: () => set({ activeOverlay: null }),

  activeView: 'chat',
  setActiveView: (view) => set({ activeView: view }),

  pendingImages: [],
  pendingFiles: [],
  addPendingAttachments: (images, files) =>
    set((s) => ({ pendingImages: [...s.pendingImages, ...images], pendingFiles: [...s.pendingFiles, ...files] })),
  removeImage: (i) => set((s) => ({ pendingImages: s.pendingImages.filter((_, j) => j !== i) })),
  removeFile: (i) => set((s) => ({ pendingFiles: s.pendingFiles.filter((_, j) => j !== i) })),
  clearAttachments: () => set({ pendingImages: [], pendingFiles: [] }),
}))
```

- [ ] **Step 3: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: errors about `openPanel`, `rightPanelOpen`, `rightPanelType` usages — these will be fixed in subsequent tasks.

- [ ] **Step 4: Commit**

```bash
git add ui/src/types/index.ts ui/src/stores/uiStore.ts
git commit -m "feat(ui): add PanelMode type and global panel store (open_panel ready)"
```

---

## Task 2: Fix App.tsx and AppShell.tsx callers

**Files:**
- Modify: `ui/src/App.tsx`
- Modify: `ui/src/components/layout/AppShell.tsx`

- [ ] **Step 1: Update `App.tsx` — remove session-coupled panel logic**

The old code opened `'canvas'` or `'music'` based on `activeSession`. That coupling is gone — the panel is now user-controlled. Replace the session effect in `ui/src/App.tsx`:

```typescript
import { useEffect } from 'react'
import AppShell from './components/layout/AppShell'
import MessageStream from './components/chat/MessageStream'
import InputBar from './components/chat/InputBar'
import SettingsDialog from './components/overlays/SettingsDialog'
import ServiceDashboard from './components/services/ServiceDashboard'
import { useChatStore } from './stores/chatStore'
import { useSessionStore } from './stores/sessionStore'
import { useUIStore } from './stores/uiStore'

export default function App() {
  const activeSession = useSessionStore((s) => s.activeSession)
  const loadHistory = useChatStore((s) => s.loadHistory)
  const activeView = useUIStore((s) => s.activeView)

  useEffect(() => {
    loadHistory(activeSession)
  }, [activeSession, loadHistory])

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
      {activeView === 'services' ? (
        <ServiceDashboard />
      ) : (
        <>
          <MessageStream />
          <InputBar />
        </>
      )}
      <SettingsDialog />
    </AppShell>
  )
}
```

- [ ] **Step 2: Update `AppShell.tsx` — remove `closePanel` on Escape**

The Escape handler for closing the panel moves into `RightPanel` itself. Remove it from `AppShell`. Find and delete this block:

```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closePanel()
  }
  window.addEventListener('keydown', handleKeyDown)
  return () => window.removeEventListener('keydown', handleKeyDown)
}, [closePanel])
```

Also remove `const closePanel = useUIStore((s) => s.closePanel)` and its import from the destructure. The `addPendingAttachments` usage stays.

- [ ] **Step 3: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: errors only from `RightPanel.tsx` which still uses old API — fix in next task.

- [ ] **Step 4: Commit**

```bash
git add ui/src/App.tsx ui/src/components/layout/AppShell.tsx
git commit -m "fix(ui): remove session-coupled panel logic from App and AppShell"
```

---

## Task 3: Rewrite RightPanel with tab bar

**Files:**
- Modify: `ui/src/components/layout/RightPanel.tsx`
- Create: `ui/src/components/panels/MusicPanel.tsx` (stub)
- Create: `ui/src/components/panels/CanvasPanel.tsx` (stub)
- Create: `ui/src/components/panels/NotesPanel.tsx` (stub)
- Create: `ui/src/components/panels/FilePanel.tsx` (stub)

- [ ] **Step 1: Create stub panel components**

`ui/src/components/panels/MusicPanel.tsx`:
```typescript
export default function MusicPanel() {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      Music — coming in Task 5
    </div>
  )
}
```

`ui/src/components/panels/CanvasPanel.tsx`:
```typescript
export default function CanvasPanel() {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      Canvas — coming in Task 6
    </div>
  )
}
```

`ui/src/components/panels/NotesPanel.tsx`:
```typescript
export default function NotesPanel() {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      Notes — coming in Task 7
    </div>
  )
}
```

`ui/src/components/panels/FilePanel.tsx`:
```typescript
interface Props {
  path?: string
  content?: string
}
export default function FilePanel({ path, content }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      {path ?? content ?? 'No file selected'}
    </div>
  )
}
```

- [ ] **Step 2: Rewrite `RightPanel.tsx`**

```typescript
import { useEffect, useCallback } from 'react'
import { useUIStore } from '../../stores/uiStore'
import type { PanelMode } from '../../types'
import MusicPanel from '../panels/MusicPanel'
import CanvasPanel from '../panels/CanvasPanel'
import NotesPanel from '../panels/NotesPanel'
import FilePanel from '../panels/FilePanel'
import Tooltip from '../ui/Tooltip'

const TABS: { mode: PanelMode; label: string; icon: React.ReactNode }[] = [
  {
    mode: 'music',
    label: 'Music',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
      </svg>
    ),
  },
  {
    mode: 'canvas',
    label: 'Canvas',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 19l7-7 3 3-7 7-3-3z" /><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" /><path d="M2 2l7.586 7.586" /><circle cx="11" cy="11" r="2" />
      </svg>
    ),
  },
  {
    mode: 'notes',
    label: 'Notes',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    mode: 'file',
    label: 'File',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" />
      </svg>
    ),
  },
]

export default function RightPanel() {
  const panelOpen = useUIStore((s) => s.panelOpen)
  const panelMode = useUIStore((s) => s.panelMode)
  const panelPayload = useUIStore((s) => s.panelPayload)
  const openPanelMode = useUIStore((s) => s.openPanelMode)
  const togglePanel = useUIStore((s) => s.togglePanel)
  const closePanel = useUIStore((s) => s.closePanel)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') closePanel()
  }, [closePanel])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const renderContent = () => {
    switch (panelMode) {
      case 'music': return <MusicPanel />
      case 'canvas': return <CanvasPanel />
      case 'notes': return <NotesPanel path={panelPayload?.path} />
      case 'file': return <FilePanel path={panelPayload?.path} content={panelPayload?.content} />
    }
  }

  return (
    <div
      className={`flex flex-col bg-surface border-l border-border h-full transition-[width] duration-200 ${
        panelOpen ? 'w-[40%] max-w-[600px]' : 'w-10'
      }`}
    >
      {/* Tab bar — always visible */}
      <div className={`flex ${panelOpen ? 'flex-row border-b border-border' : 'flex-col'} items-center`}>
        {/* Toggle button */}
        <Tooltip text={panelOpen ? 'Close panel' : 'Open panel'} side={panelOpen ? 'top' : 'right'}>
          <button
            onClick={togglePanel}
            className="flex items-center justify-center w-10 h-10 flex-shrink-0 text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
          >
            <svg
              width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              className={`transition-transform ${panelOpen ? 'rotate-0' : 'rotate-180'}`}
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </Tooltip>

        {/* Mode tabs */}
        {TABS.map(({ mode, label, icon }) => (
          <Tooltip key={mode} text={label} side={panelOpen ? 'top' : 'right'} disabled={panelOpen}>
            <button
              onClick={() => openPanelMode(mode)}
              className={`flex items-center gap-2 px-3 h-10 text-sm transition-colors cursor-pointer ${
                panelOpen && panelMode === mode
                  ? 'text-accent border-b-2 border-accent'
                  : 'text-text-tertiary hover:text-text-primary'
              } ${!panelOpen ? 'w-10 justify-center' : ''}`}
            >
              {icon}
              {panelOpen && <span>{label}</span>}
            </button>
          </Tooltip>
        ))}
      </div>

      {/* Content */}
      {panelOpen && (
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          {renderContent()}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors.

- [ ] **Step 4: Start dev server and verify the tab bar renders**

```bash
cd ui && npm run dev
```

Open browser at `http://localhost:5173`. Right side should show a collapsed strip with mode icons. Clicking any icon should expand the panel and show a stub message. Clicking the toggle arrow should collapse/expand. Pressing Escape should close.

- [ ] **Step 5: Commit**

```bash
git add ui/src/components/layout/RightPanel.tsx ui/src/components/panels/
git commit -m "feat(ui): right panel tab bar with Music/Canvas/Notes/File modes"
```

---

## Task 4: Handle `open_panel` SSE chunk in InputBar

**Files:**
- Modify: `ui/src/components/chat/InputBar.tsx`

The model can now emit `{ type: 'open_panel', mode: 'notes', payload: { path: 'Some Note.md' } }` and the UI will open the panel to that mode.

- [ ] **Step 1: Add `open_panel` handler to the SSE loop in `InputBar.tsx`**

Find the SSE chunk parsing loop (around line 116 in the current file). Add a new branch after `approval_request`:

```typescript
// add to imports at top of file:
// openPanelMode is already accessible via useUIStore.getState()

// Inside the SSE for-loop, after the approval_request branch:
} else if (chunk.type === 'open_panel') {
  useUIStore.getState().openPanelMode(chunk.mode, chunk.payload)
}
```

The full updated block (replace the existing `try { const chunk = JSON.parse(raw) ...` block):

```typescript
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
  } else if (chunk.type === 'open_panel') {
    useUIStore.getState().openPanelMode(chunk.mode, chunk.payload)
  }
} catch { /* malformed chunk */ }
```

- [ ] **Step 2: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add ui/src/components/chat/InputBar.tsx
git commit -m "feat(ui): handle open_panel SSE chunk to open workspace panel"
```

---

## Task 5: Backend — emit `open_panel` SSE chunk

**Files:**
- Modify: `bootstrap/agents/chat_agent.py`

Tools can already return `{ "__type": "canvas_command", ... }` and `{ "__type": "play_queue", ... }`. Add handling for `__type == "open_panel"` so any tool can trigger the panel.

- [ ] **Step 1: Add `open_panel` emission in `chat_agent.py`**

Find the tool result handling block (around line 289 in current code). After the `canvas_command` branch, add:

```python
elif isinstance(result, dict) and result.get("__type") == "open_panel":
    mode = result.get("mode", "file")
    payload = result.get("payload", {})
    summary = result.get("summary", f"Opening {mode} panel.")
    yield json.dumps({"type": "open_panel", "mode": mode, "payload": payload})
    yield json.dumps({"type": "tool_result", "tool": tool_name, "output": summary})
    tool_result_parts.append(
        f"<tool_result>\n<function={tool_name}>\n{summary}\n</function>\n</tool_result>"
    )
```

- [ ] **Step 2: Restart bootstrap and verify no startup errors**

```bash
cd /home/rezxt/bootstrap && .venv/bin/python main.py
```

Expected: server starts on port 8100 with no import errors.

- [ ] **Step 3: Commit**

```bash
git add bootstrap/agents/chat_agent.py
git commit -m "feat(backend): emit open_panel SSE chunk from tool results"
```

---

## Task 6: Backend — Notes API

**Files:**
- Create: `bootstrap/api/notes.py`
- Modify: `bootstrap/main.py`

This adds three endpoints the Notes panel will call:
- `GET /notes/tree` — returns the vault directory tree as JSON
- `GET /notes/file?path=<vault-relative-path>` — returns raw markdown content
- `PUT /notes/file` — writes markdown content back to the vault file

The vault root is `/mnt/WD/The Ideas`. All paths are sandboxed to that root (no `..` traversal).

- [ ] **Step 1: Create `bootstrap/api/notes.py`**

```python
import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/notes", tags=["notes"])

VAULT_ROOT = "/mnt/WD/The Ideas"


def _safe_path(rel: str) -> str:
    """Resolve a vault-relative path and reject traversal attempts."""
    full = os.path.realpath(os.path.join(VAULT_ROOT, rel))
    if not full.startswith(os.path.realpath(VAULT_ROOT)):
        raise HTTPException(status_code=400, detail="Path outside vault")
    return full


def _build_tree(root: str, rel: str = "") -> list[dict]:
    """Recursively build a file tree, markdown files only."""
    entries = []
    try:
        items = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []
    for item in items:
        if item.name.startswith('.') or item.name.startswith('_'):
            continue
        item_rel = os.path.join(rel, item.name) if rel else item.name
        if item.is_dir():
            children = _build_tree(item.path, item_rel)
            if children:
                entries.append({"name": item.name, "path": item_rel, "type": "dir", "children": children})
        elif item.name.endswith('.md'):
            entries.append({"name": item.name, "path": item_rel, "type": "file"})
    return entries


@router.get("/tree")
async def get_tree():
    return _build_tree(VAULT_ROOT)


@router.get("/file")
async def get_file(path: str = Query(...)):
    full = _safe_path(path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    with open(full, encoding="utf-8") as f:
        return {"path": path, "content": f.read()}


class WriteBody(BaseModel):
    path: str
    content: str


@router.put("/file")
async def put_file(body: WriteBody):
    full = _safe_path(body.path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"ok": True}
```

- [ ] **Step 2: Register the router in `bootstrap/main.py`**

Find where the other routers are imported and registered (look for `app.include_router(canvas.router)` or similar). Add:

```python
from api import notes
# ...
app.include_router(notes.router)
```

- [ ] **Step 3: Restart and smoke-test**

```bash
cd /home/rezxt/bootstrap && .venv/bin/python main.py &
sleep 2
curl http://localhost:8100/notes/tree | python3 -m json.tool | head -30
```

Expected: JSON array of vault files and folders.

```bash
curl "http://localhost:8100/notes/file?path=Accel_Roadmap.md" | python3 -m json.tool | head -10
```

Expected: `{"path": "Accel_Roadmap.md", "content": "..."}`.

- [ ] **Step 4: Commit**

```bash
git add bootstrap/api/notes.py bootstrap/main.py
git commit -m "feat(backend): notes API — tree browse, file read/write from Obsidian vault"
```

---

## Task 7: MusicPanel — now playing + controls

**Files:**
- Modify: `ui/src/components/panels/MusicPanel.tsx`

The `playerStore` already has `nowPlaying`, `fetchNowPlaying`, `playPause`, `next`, `previous`, `seek`, `queue`. This panel polls every 3s when Feishin is the source, or reads live from the in-browser `audioElement` queue.

- [ ] **Step 1: Implement `MusicPanel.tsx`**

```typescript
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
```

- [ ] **Step 2: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors.

- [ ] **Step 3: Open the Music tab in the panel and verify it shows the now-playing state (or the placeholder art if nothing is playing)**

Start dev server, click the music note icon in the right panel, check that controls render.

- [ ] **Step 4: Commit**

```bash
git add ui/src/components/panels/MusicPanel.tsx
git commit -m "feat(ui): music panel with now-playing, progress bar, controls, queue"
```

---

## Task 8: CanvasPanel — tldraw

**Files:**
- Modify: `ui/src/components/panels/CanvasPanel.tsx`

The canvas was previously in the old blob UI. For now the simplest correct implementation is an iframe pointing to a dedicated canvas page, or a direct tldraw embed. Since the current tech stack is Vite/React, we embed tldraw directly.

tldraw is not yet a dependency — add it, then embed. State is saved to `/canvas/state` on the backend (already exists: `GET /canvas/state`, `POST /canvas/state`).

- [ ] **Step 1: Install tldraw**

```bash
cd ui && npm install tldraw@2.4.0
```

Expected: tldraw and its peer deps installed.

- [ ] **Step 2: Implement `CanvasPanel.tsx`**

```typescript
import { useEffect, useCallback, useRef } from 'react'
import { Tldraw, type Editor } from 'tldraw'
import 'tldraw/tldraw.css'

async function loadState(): Promise<object | null> {
  try {
    const res = await fetch('/canvas/state')
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

async function saveState(snapshot: object) {
  await fetch('/canvas/state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(snapshot),
  })
}

export default function CanvasPanel() {
  const editorRef = useRef<Editor | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleMount = useCallback(async (editor: Editor) => {
    editorRef.current = editor
    const state = await loadState()
    if (state && Object.keys(state).length > 0) {
      editor.loadSnapshot(state as any)
    }
  }, [])

  const handleChange = useCallback(() => {
    if (!editorRef.current) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      if (editorRef.current) {
        saveState(editorRef.current.getSnapshot())
      }
    }, 1000)
  }, [])

  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current) }, [])

  return (
    <div className="flex-1 relative">
      <Tldraw
        onMount={handleMount}
        onChange={handleChange}
        hideUi={false}
      />
    </div>
  )
}
```

- [ ] **Step 3: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors. If tldraw types complain about `onChange`, use `onEditorChange` or wrap in a `useEffect` on the editor's `store.listen` — tldraw's API uses `editor.store.listen(callback)` for change events. Use this alternative if `onChange` prop does not exist:

```typescript
const handleMount = useCallback(async (editor: Editor) => {
  editorRef.current = editor
  const state = await loadState()
  if (state && Object.keys(state).length > 0) {
    editor.loadSnapshot(state as any)
  }
  editor.store.listen(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      saveState(editor.getSnapshot())
    }, 1000)
  }, { source: 'user', scope: 'all' })
}, [])

// Remove onChange prop from <Tldraw>
```

- [ ] **Step 4: Open Canvas tab and verify tldraw loads, drawing persists after refresh**

Start dev server, click Canvas tab, draw something, wait 1s, refresh page, reopen Canvas tab — shapes should still be there.

- [ ] **Step 5: Commit**

```bash
git add ui/src/components/panels/CanvasPanel.tsx ui/package.json ui/package-lock.json
git commit -m "feat(ui): canvas panel with tldraw, auto-save to /canvas/state"
```

---

## Task 9: NotesPanel — file tree + markdown viewer/editor

**Files:**
- Modify: `ui/src/components/panels/NotesPanel.tsx`

This is the most complex panel. It has two sub-sections:
- Left: collapsible file tree (from `GET /notes/tree`)
- Right: markdown content area with toggle between rendered view and raw edit mode

`formatMarkdown` (from `../../lib/format`) already handles markdown → HTML rendering.

- [ ] **Step 1: Implement `NotesPanel.tsx`**

```typescript
import { useState, useEffect, useCallback } from 'react'
import { formatMarkdown } from '../../lib/format'

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'dir'
  children?: TreeNode[]
}

interface Props {
  path?: string
}

function TreeItem({
  node,
  selectedPath,
  onSelect,
  depth,
}: {
  node: TreeNode
  selectedPath: string | null
  onSelect: (path: string) => void
  depth: number
}) {
  const [expanded, setExpanded] = useState(depth < 1)

  if (node.type === 'dir') {
    return (
      <div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-text-secondary hover:text-text-primary transition-colors cursor-pointer text-left"
          style={{ paddingLeft: `${8 + depth * 12}px` }}
        >
          <svg
            width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            className={`flex-shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children?.map((child) => (
          <TreeItem key={child.path} node={child} selectedPath={selectedPath} onSelect={onSelect} depth={depth + 1} />
        ))}
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      className={`w-full flex items-center gap-1.5 py-1 text-xs truncate transition-colors cursor-pointer text-left ${
        selectedPath === node.path
          ? 'text-accent bg-accent-soft'
          : 'text-text-secondary hover:text-text-primary'
      }`}
      style={{ paddingLeft: `${20 + depth * 12}px` }}
    >
      <span className="truncate">{node.name.replace(/\.md$/, '')}</span>
    </button>
  )
}

export default function NotesPanel({ path: initialPath }: Props) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [selectedPath, setSelectedPath] = useState<string | null>(initialPath ?? null)
  const [content, setContent] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [treeOpen, setTreeOpen] = useState(true)

  useEffect(() => {
    fetch('/notes/tree')
      .then((r) => r.json())
      .then(setTree)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedPath) return
    fetch(`/notes/file?path=${encodeURIComponent(selectedPath)}`)
      .then((r) => r.json())
      .then((d) => {
        setContent(d.content ?? '')
        setDirty(false)
      })
      .catch(() => {})
  }, [selectedPath])

  // If panel opened with a path prop, select it
  useEffect(() => {
    if (initialPath) setSelectedPath(initialPath)
  }, [initialPath])

  const save = useCallback(async () => {
    if (!selectedPath || !dirty) return
    setSaving(true)
    await fetch('/notes/file', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: selectedPath, content }),
    })
    setSaving(false)
    setDirty(false)
  }, [selectedPath, content, dirty])

  const handleEdit = (val: string) => {
    setContent(val)
    setDirty(true)
  }

  return (
    <div className="flex h-full min-h-0">
      {/* File tree sidebar */}
      {treeOpen && (
        <div className="w-48 flex-shrink-0 border-r border-border overflow-y-auto py-2">
          {tree.map((node) => (
            <TreeItem key={node.path} node={node} selectedPath={selectedPath} onSelect={setSelectedPath} depth={0} />
          ))}
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-3 h-9 border-b border-border flex-shrink-0">
          <button
            onClick={() => setTreeOpen((v) => !v)}
            className="text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
            title="Toggle file tree"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>

          <span className="text-xs text-text-tertiary truncate flex-1">
            {selectedPath ? selectedPath.replace(/\.md$/, '') : 'Select a note'}
          </span>

          {selectedPath && (
            <>
              <button
                onClick={() => setEditMode((v) => !v)}
                className={`text-xs px-2 py-0.5 rounded transition-colors cursor-pointer ${
                  editMode ? 'text-accent bg-accent-soft' : 'text-text-tertiary hover:text-text-primary'
                }`}
              >
                {editMode ? 'Preview' : 'Edit'}
              </button>
              {dirty && (
                <button
                  onClick={save}
                  disabled={saving}
                  className="text-xs px-2 py-0.5 rounded bg-accent text-white hover:bg-violet-500 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
              )}
            </>
          )}
        </div>

        {/* Editor or rendered view */}
        <div className="flex-1 min-h-0 overflow-auto">
          {!selectedPath ? (
            <div className="flex items-center justify-center h-full text-text-tertiary text-sm">
              Select a note from the sidebar
            </div>
          ) : editMode ? (
            <textarea
              value={content}
              onChange={(e) => handleEdit(e.target.value)}
              className="w-full h-full p-4 bg-transparent text-sm text-text-primary font-mono outline-none resize-none leading-relaxed"
              spellCheck={false}
            />
          ) : (
            <div
              className="p-4 text-sm leading-relaxed prose-invert [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mb-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_a:hover]:text-blue-300 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-text-secondary"
              dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors.

- [ ] **Step 3: Start dev server and smoke-test**

Open the Notes tab. File tree should load from `/notes/tree`. Click a file — content loads. Click Edit — textarea appears with raw markdown. Modify text — Save button appears. Click Save — content written back to vault file.

- [ ] **Step 4: Commit**

```bash
git add ui/src/components/panels/NotesPanel.tsx
git commit -m "feat(ui): notes panel with file tree, markdown viewer, and inline editor"
```

---

## Task 10: FilePanel — generic viewer

**Files:**
- Modify: `ui/src/components/panels/FilePanel.tsx`

The File panel is the fallback mode when the model opens a file that isn't a vault note — e.g. a screenshot, a code file read by a tool, or an image result. It handles: images (base64 or URL), code/text (with syntax hint), and a plain text fallback.

- [ ] **Step 1: Implement `FilePanel.tsx`**

```typescript
import { formatMarkdown } from '../../lib/format'

interface Props {
  path?: string
  content?: string
}

function isImagePath(path: string) {
  return /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(path)
}

function isBase64Image(content: string) {
  return content.startsWith('data:image/')
}

export default function FilePanel({ path, content }: Props) {
  if (!path && !content) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
        No file selected
      </div>
    )
  }

  // Image via URL or base64
  if ((path && isImagePath(path)) || (content && isBase64Image(content))) {
    const src = content ?? path!
    return (
      <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
        <img src={src} alt={path ?? 'image'} className="max-w-full max-h-full rounded-md object-contain" />
      </div>
    )
  }

  // Markdown
  if (path?.endsWith('.md') && content) {
    return (
      <div
        className="flex-1 p-4 overflow-auto text-sm leading-relaxed prose-invert [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mb-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:rounded"
        dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }}
      />
    )
  }

  // Code / plain text
  return (
    <div className="flex-1 overflow-auto p-4">
      <pre className="text-xs font-mono text-text-secondary whitespace-pre-wrap break-words leading-relaxed">
        {content ?? `Path: ${path}`}
      </pre>
    </div>
  )
}
```

- [ ] **Step 2: Run type check**

```bash
cd ui && npx tsc -p tsconfig.app.json --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add ui/src/components/panels/FilePanel.tsx
git commit -m "feat(ui): file panel — image, markdown, and plain text viewer"
```

---

## Self-Review

**Spec coverage:**
- ✅ Tab bar with Music / Canvas / Notes / File modes — Task 3
- ✅ Panel persists mode across sessions — `panelMode` in Zustand (not reset on session switch)
- ✅ Model can open panel via SSE `open_panel` — Tasks 4 & 5
- ✅ Model can switch to a specific mode with optional payload (path) — `openPanelMode(mode, payload)` in store
- ✅ Notes: file tree browsing Obsidian vault — Task 9 (file tree component)
- ✅ Notes: markdown rendered view — Task 9 (dangerouslySetInnerHTML with formatMarkdown)
- ✅ Notes: edit mode (raw textarea) + save back to vault — Task 9 + Task 6 PUT endpoint
- ✅ Music player moves to panel — Task 7
- ✅ Canvas moves to panel — Task 8
- ✅ File viewer (images, code, md) — Task 10
- ✅ Escape closes panel — Task 3 (useEffect in RightPanel)

**Placeholder scan:** None found — all tasks contain full code.

**Type consistency:**
- `PanelMode` defined in Task 1, used in Tasks 3, 4, 5
- `OpenPanelPayload` defined in Task 1, used in Tasks 3, 4
- `openPanelMode(mode, payload?)` defined in Task 1, called in Tasks 3 and 4
- `NotesPanel` receives `path?: string`, passed from `panelPayload?.path` in Task 3
- `FilePanel` receives `path?: string, content?: string`, passed from `panelPayload` in Task 3
- `TreeNode` defined locally in Task 9 — consistent
