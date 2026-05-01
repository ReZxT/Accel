import { useEffect, useCallback, useRef } from 'react'
import { Tldraw, exportToBlob, type Editor } from 'tldraw'
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

async function savePng(editor: Editor) {
  try {
    const ids = [...editor.getCurrentPageShapeIds()]
    if (ids.length === 0) return
    const blob = await exportToBlob({ editor, ids, format: 'png' })
    const buf = await blob.arrayBuffer()
    const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
    await fetch('/canvas/png', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: b64 }),
    })
  } catch { /* non-critical */ }
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
    editor.store.listen(() => savePng(editor), { source: 'user', scope: 'all' })

    ;(window as any)._canvasCommand = (command: string, data: any) => {
      if (command === 'tldraw:clear') {
        editor.selectAll()
        editor.deleteShapes(editor.getSelectedShapeIds())
        return
      }
      if (command === 'tldraw:create_shapes') {
        const shapes = (data.shapes ?? []).map((s: any) => {
          const { type, x = 100, y = 100, ...rest } = s
          const props: Record<string, any> = {}
          if (type === 'geo') {
            props.geo = rest.geo ?? 'rectangle'
            props.w = rest.w ?? 200
            props.h = rest.h ?? 80
            props.text = rest.text ?? ''
            props.color = rest.color ?? 'blue'
            props.fill = rest.fill ?? 'none'
            props.size = rest.size ?? 'm'
          } else if (type === 'text') {
            props.text = rest.text ?? ''
            props.color = rest.color ?? 'black'
            props.size = rest.size ?? 'm'
          } else if (type === 'note') {
            props.text = rest.text ?? ''
            props.color = rest.color ?? 'yellow'
            props.size = rest.size ?? 'm'
          } else if (type === 'arrow') {
            props.color = rest.color ?? 'black'
            props.size = rest.size ?? 'm'
          }
          return { type, x, y, props }
        })
        editor.createShapes(shapes)
        setTimeout(() => savePng(editor), 300)
      }
    }
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
