import { useState, useRef, useCallback } from 'react'
import { useChatStore } from '../../stores/chatStore'
import { useSessionStore } from '../../stores/sessionStore'
import { useUIStore } from '../../stores/uiStore'

export default function InputBar() {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const isLoading = useChatStore((s) => s.isLoading)
  const cancelStream = useChatStore((s) => s.cancelStream)
  const activeSession = useSessionStore((s) => s.activeSession)
  const pendingImages = useUIStore((s) => s.pendingImages)
  const pendingFiles = useUIStore((s) => s.pendingFiles)
  const addPendingAttachments = useUIStore((s) => s.addPendingAttachments)
  const removeImage = useUIStore((s) => s.removeImage)
  const removeFile = useUIStore((s) => s.removeFile)
  const clearAttachments = useUIStore((s) => s.clearAttachments)

  const handleFiles = useCallback(async (fileList: FileList) => {
    const IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp'])
    const LANGUAGE_MAP: Record<string, string> = {
      ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
      py: 'python', rs: 'rust', go: 'go', cpp: 'cpp', c: 'c', cs: 'csharp',
      java: 'java', rb: 'ruby', sh: 'bash', md: 'markdown', json: 'json',
      yaml: 'yaml', yml: 'yaml', toml: 'toml', html: 'html', css: 'css',
    }
    const imgs = []
    const files = []
    for (const file of Array.from(fileList)) {
      if (IMAGE_TYPES.has(file.type)) {
        const base64 = await new Promise<string>((res, rej) => {
          const r = new FileReader()
          r.onload = () => res((r.result as string).split(',')[1])
          r.onerror = rej
          r.readAsDataURL(file)
        })
        imgs.push({ base64, name: file.name, type: file.type, dataUrl: `data:${file.type};base64,${base64}` })
      } else {
        const content = await new Promise<string>((res, rej) => {
          const r = new FileReader()
          r.onload = () => res(r.result as string)
          r.onerror = rej
          r.readAsText(file)
        })
        const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
        files.push({ content, name: file.name, language: LANGUAGE_MAP[ext] ?? '' })
      }
    }
    addPendingAttachments(imgs, files)
  }, [addPendingAttachments])

  const handleSend = useCallback(() => {
    if (isLoading) {
      cancelStream(activeSession)
      return
    }
    const trimmed = text.trim()
    if (!trimmed && pendingImages.length === 0 && pendingFiles.length === 0) return

    const { addMessage, startLoading, appendStreamText, appendStreamThinking, addStreamToolCall, addStreamToolResult, addStreamApproval, finishStreaming } = useChatStore.getState()

    const images = useUIStore.getState().pendingImages
    const files = useUIStore.getState().pendingFiles

    addMessage({
      role: 'user' as const,
      content: trimmed || (images.length > 0 ? '[image]' : '[file]'),
      timestamp: new Date().toISOString(),
      images: images.length > 0 ? images : undefined,
      files: files.length > 0 ? files : undefined,
    })
    setText('')
    clearAttachments()
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const controller = new AbortController()
    startLoading(controller)

    const messages = useChatStore.getState().messages
    const payload = {
      chatInput: trimmed || (images.length > 0 ? 'What do you see?' : 'Describe this file.'),
      chatHistory: messages.slice(-60).map((m) =>
        m.role === 'bot' ? { ...m, role: 'assistant' } : m,
      ),
      sessionId: activeSession,
      images: images.map(({ base64, name, type }) => ({ base64, name, type })),
      files: files.map(({ content, name, language }) => ({ content, name, language })),
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
              } else if (chunk.type === 'open_panel') {
                useUIStore.getState().openPanelMode(chunk.mode, chunk.payload)
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
  }, [text, isLoading, activeSession, cancelStream, pendingImages.length, pendingFiles.length, clearAttachments])

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

  const hasAttachments = pendingImages.length > 0 || pendingFiles.length > 0

  return (
    <div className="px-4 pb-4 pt-2">
      {/* Attachment previews */}
      {hasAttachments && (
        <div className="flex flex-wrap gap-2 mb-2">
          {pendingImages.map((img, i) => (
            <div key={i} className="relative group">
              <img src={img.dataUrl} alt={img.name} className="h-16 w-16 object-cover rounded-md border border-border" />
              <button
                onClick={() => removeImage(i)}
                className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-error text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              >×</button>
            </div>
          ))}
          {pendingFiles.map((f, i) => (
            <div key={i} className="relative group flex items-center gap-1.5 bg-surface border border-border rounded-md px-2 py-1">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-tertiary flex-shrink-0"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span className="text-xs text-text-secondary max-w-[120px] truncate">{f.name}</span>
              <button
                onClick={() => removeFile(i)}
                className="text-text-tertiary hover:text-error transition-colors ml-1 cursor-pointer"
              >×</button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 bg-surface border border-border rounded-lg px-3 py-3 focus-within:border-border-hi transition-colors">
        {/* Attachment button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex-shrink-0 mb-0.5 p-1.5 rounded-md text-text-tertiary hover:text-text-secondary hover:bg-white/5 transition-colors cursor-pointer"
          title="Attach file or image"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,text/*,.py,.ts,.tsx,.js,.jsx,.rs,.go,.cpp,.c,.cs,.java,.rb,.sh,.md,.json,.yaml,.yml,.toml"
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />

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
          className={`flex-shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-colors cursor-pointer ${
            isLoading
              ? 'bg-error text-white hover:bg-red-500'
              : 'bg-accent text-white hover:bg-violet-500'
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
