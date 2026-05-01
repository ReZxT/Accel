import { useEffect, useCallback, useRef } from 'react'
import { Tldraw, type Editor } from 'tldraw'
import 'tldraw/tldraw.css'

async function loadState(): Promise<object | null> {
  try {
    const res = await fetch('/canvas/state')
    if (!res.ok) return null
    const data = await res.json()
    return Object.keys(data).length > 0 ? data : null
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

  const scheduleSave = useCallback(() => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      if (editorRef.current) {
        saveState(editorRef.current.getSnapshot())
      }
    }, 1000)
  }, [])

  const handleMount = useCallback((editor: Editor) => {
    editorRef.current = editor
    loadState().then((state) => {
      if (state) {
        try {
          editor.loadSnapshot(state as any)
        } catch { /* ignore incompatible snapshot */ }
      }
    })
    editor.store.listen(scheduleSave, { source: 'user', scope: 'all' })
  }, [scheduleSave])

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
  }, [])

  return (
    <div className="flex-1 relative" style={{ height: '100%' }}>
      <Tldraw onMount={handleMount} />
    </div>
  )
}
