import { useState, useEffect, useCallback } from 'react'
import DOMPurify from 'dompurify'
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
    try {
      const res = await fetch('/notes/file', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedPath, content }),
      })
      if (res.ok) setDirty(false)
    } catch {
      // leave dirty=true so user can retry
    } finally {
      setSaving(false)
    }
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
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(formatMarkdown(content)) }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
