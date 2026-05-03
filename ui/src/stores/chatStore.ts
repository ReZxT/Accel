import { create } from 'zustand'
import type {
  Message,
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
  modelId: string | null

  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  appendStreamText: (text: string) => void
  replaceStreamText: (text: string) => void
  appendStreamThinking: (text: string) => void
  addStreamToolCall: (tc: StreamingToolCall) => void
  addStreamToolResult: (tr: StreamingToolResult) => void
  addStreamApproval: (a: StreamingApproval) => void
  resolveApproval: (requestId: string, approved: boolean) => void
  setModelId: (id: string | null) => void

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
  modelId: null,

  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  appendStreamText: (text) =>
    set((s) => ({ streamingText: s.streamingText + text })),
  replaceStreamText: (text) =>
    set({ streamingText: text }),
  appendStreamThinking: (text) =>
    set((s) => ({ streamingThinking: s.streamingThinking + text })),
  addStreamToolCall: (tc) =>
    set((s) => ({ streamingTools: [...s.streamingTools, tc] })),
  addStreamToolResult: (tr) =>
    set((s) => ({ streamingResults: [...s.streamingResults, tr] })),
  addStreamApproval: (a) =>
    set({ streamingApprovals: [a] }),
  resolveApproval: (requestId, approved) =>
    set((s) => ({
      streamingApprovals: s.streamingApprovals.map((a) =>
        a.request_id === requestId ? { ...a, resolved: true, approved } : a,
      ),
    })),
  setModelId: (id) => set({ modelId: id }),

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
    const { streamingText, streamingThinking, streamingTools, messages } = get()
    if (streamingText.trim() || streamingThinking || streamingTools.length > 0) {
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
