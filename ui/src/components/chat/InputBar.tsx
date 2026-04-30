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
