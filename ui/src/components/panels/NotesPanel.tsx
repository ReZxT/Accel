import { useState, useEffect, useCallback } from 'react'
import DOMPurify from 'dompurify'
import { formatMarkdown } from '../../lib/format'

interface TreeNode {
  name: string
  path: string
  type: 'file' | 'dir'
  children?: TreeNode[]
}

interface Vault {
  id: string
  name: string
  path: string
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

function AddVaultForm({ onAdd }: { onAdd: (vault: Vault) => void }) {
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [error, setError] = useState('')

  const submit = async () => {
    if (!name.trim() || !path.trim()) return
    setError('')
    const res = await fetch('/notes/vaults', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim(), path: path.trim() }),
    })
    if (res.ok) {
      const vault = await res.json()
      onAdd(vault)
      setName('')
      setPath('')
    } else {
      const d = await res.json().catch(() => ({}))
      setError(d.detail ?? 'Failed to add vault')
    }
  }

  return (
    <div className="p-3 border-t border-border flex flex-col gap-2">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Vault name"
        className="w-full text-xs bg-black/20 border border-border rounded px-2 py-1 text-text-primary placeholder-text-tertiary outline-none focus:border-accent"
      />
      <input
        value={path}
        onChange={(e) => setPath(e.target.value)}
        placeholder="/path/to/vault"
        className="w-full text-xs bg-black/20 border border-border rounded px-2 py-1 text-text-primary placeholder-text-tertiary outline-none focus:border-accent font-mono"
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button
        onClick={submit}
        className="text-xs px-2 py-1 rounded bg-accent text-white hover:bg-violet-500 transition-colors cursor-pointer"
      >
        Add vault
      </button>
    </div>
  )
}

export default function NotesPanel({ path: initialPath }: Props) {
  const [vaults, setVaults] = useState<Vault[]>([])
  const [activeVault, setActiveVault] = useState<string>('default')
  const [showVaultManager, setShowVaultManager] = useState(false)
  const [tree, setTree] = useState<TreeNode[]>([])
  const [selectedPath, setSelectedPath] = useState<string | null>(initialPath ?? null)
  const [content, setContent] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [treeOpen, setTreeOpen] = useState(true)

  useEffect(() => {
    fetch('/notes/vaults')
      .then((r) => r.json())
      .then((data: Vault[]) => {
        setVaults(data)
        if (data.length > 0 && !data.find((v) => v.id === activeVault)) {
          setActiveVault(data[0].id)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setTree([])
    setSelectedPath(null)
    setContent('')
    fetch(`/notes/tree?vault=${activeVault}`)
      .then((r) => r.json())
      .then(setTree)
      .catch(() => {})
  }, [activeVault])

  useEffect(() => {
    if (!selectedPath) return
    fetch(`/notes/file?path=${encodeURIComponent(selectedPath)}&vault=${activeVault}`)
      .then((r) => r.json())
      .then((d) => {
        setContent(d.content ?? '')
        setDirty(false)
      })
      .catch(() => {})
  }, [selectedPath, activeVault])

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
        body: JSON.stringify({ path: selectedPath, content, vault: activeVault }),
      })
      if (res.ok) setDirty(false)
    } catch {
      // leave dirty=true so user can retry
    } finally {
      setSaving(false)
    }
  }, [selectedPath, content, dirty, activeVault])

  const handleEdit = (val: string) => {
    setContent(val)
    setDirty(true)
  }

  const deleteVault = async (id: string) => {
    const res = await fetch(`/notes/vaults/${id}`, { method: 'DELETE' })
    if (res.ok) setVaults((v) => v.filter((x) => x.id !== id))
    if (id === activeVault) setActiveVault(vaults.find((v) => v.id !== id)?.id ?? 'default')
  }

  const activeVaultName = vaults.find((v) => v.id === activeVault)?.name ?? 'Notes'

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Vault bar */}
      <div className="flex items-center gap-1 px-3 h-8 border-b border-border flex-shrink-0 bg-black/10">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-tertiary flex-shrink-0">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
        </svg>
        <select
          value={activeVault}
          onChange={(e) => setActiveVault(e.target.value)}
          className="flex-1 text-xs bg-transparent text-text-secondary outline-none cursor-pointer"
        >
          {vaults.map((v) => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
        <button
          onClick={() => setShowVaultManager((v) => !v)}
          className={`text-xs px-1.5 py-0.5 rounded transition-colors cursor-pointer ${showVaultManager ? 'text-accent' : 'text-text-tertiary hover:text-text-primary'}`}
          title="Manage vaults"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>

      {/* Vault manager panel */}
      {showVaultManager && (
        <div className="border-b border-border bg-black/20 flex-shrink-0">
          <div className="px-3 py-2">
            <p className="text-xs text-text-tertiary mb-2 font-medium">Vaults</p>
            {vaults.map((v) => (
              <div key={v.id} className="flex items-center gap-2 py-1">
                <span className="text-xs text-text-primary flex-1 truncate">{v.name}</span>
                <span className="text-xs text-text-tertiary font-mono truncate max-w-[120px]">{v.path}</span>
                {v.id !== 'default' && (
                  <button
                    onClick={() => deleteVault(v.id)}
                    className="text-text-tertiary hover:text-red-400 transition-colors cursor-pointer flex-shrink-0"
                  >
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6M14 11v6" /><path d="M9 6V4h6v2" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
          <AddVaultForm onAdd={(v) => setVaults((prev) => [...prev, v])} />
        </div>
      )}

      {/* Main content: tree + editor */}
      <div className="flex flex-1 min-h-0">
        {/* File tree sidebar */}
        {treeOpen && (
          <div className="w-48 flex-shrink-0 border-r border-border overflow-y-auto py-2">
            {tree.length === 0 ? (
              <p className="text-xs text-text-tertiary px-3 py-2">No notes found</p>
            ) : (
              tree.map((node) => (
                <TreeItem key={node.path} node={node} selectedPath={selectedPath} onSelect={setSelectedPath} depth={0} />
              ))
            )}
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
              {selectedPath ? selectedPath.replace(/\.md$/, '') : `${activeVaultName} — select a note`}
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
    </div>
  )
}
