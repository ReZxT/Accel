import { useState, useEffect } from 'react'
import { useUIStore } from '../../stores/uiStore'
import { useChatStore } from '../../stores/chatStore'
import { useSessionStore } from '../../stores/sessionStore'
import { getToolSettings, updateToolSettings } from '../../api/tools'
import { toggleVoice, getVoiceStatus } from '../../api/voice'
import { getModels, setActiveModel } from '../../api/models'
import { isElectron } from '../../api/electron'
import type { ToolPolicy } from '../../types'
import type { ModelInfo } from '../../api/models'

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
  const modelId = useChatStore((s) => s.modelId)
  const setModelId = useChatStore((s) => s.setModelId)
  const [toolSettings, setToolSettings] = useState<Record<string, ToolPolicy>>({})
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [activeChatModel, setActiveChatModel] = useState('')

  useEffect(() => {
    if (activeOverlay === 'settings') {
      getToolSettings().then(setToolSettings).catch(() => {})
      getVoiceStatus().then(setVoiceEnabled).catch(() => {})
      getModels().then((s) => {
        setModels(s.available)
        setActiveChatModel(s.chat_model_id)
      }).catch(() => {})
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

  const handleModelChange = (id: string) => {
    setActiveModel('chat', id).then(() => {
      setActiveChatModel(id)
      if (id === modelId) setModelId(null) // "default" — use registry default
      else setModelId(id)
    }).catch(() => {})
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

          {/* Model selector */}
          <div>
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              Model
            </h3>
            <div className="space-y-1.5">
              {models.length === 0 && (
                <p className="text-xs text-text-tertiary">Loading models...</p>
              )}
              {models.map((m) => (
                <button
                  key={m.id}
                  onClick={() => handleModelChange(m.id)}
                  disabled={m.id === activeChatModel}
                  className={`w-full text-left px-3 py-2 rounded-md border text-xs transition-colors cursor-pointer ${
                    m.id === activeChatModel
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-text-secondary hover:border-accent/50 hover:bg-surface-hover'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{m.name}</span>
                    <span className="text-text-tertiary font-mono text-[10px] uppercase">{m.provider.replace('_', ' ')}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-text-tertiary">
                    <span>{m.context_window >= 1000 ? `${(m.context_window / 1000).toFixed(0)}k ctx` : `${m.context_window} ctx`}</span>
                    {m.supports_vision && <span>👁 vision</span>}
                    {m.supports_thinking && <span>🧠 thinking</span>}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Clear chat */}
          <button
            onClick={() => { clearChat(activeSession); closeOverlay() }}
            className="text-sm text-error hover:text-error/80 transition-colors"
          >
            Clear Chat
          </button>

          {/* DevTools — Electron dev only */}
          {isElectron() && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-secondary">Developer Tools</span>
              <button
                onClick={() => window.accel?.window.openDevTools()}
                className="text-xs px-3 py-1 rounded border border-border text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors cursor-pointer"
              >
                Open DevTools
              </button>
            </div>
          )}

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
