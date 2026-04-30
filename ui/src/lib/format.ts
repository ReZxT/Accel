import { marked } from 'marked'

export function formatMarkdown(text: string): string {
  try {
    return marked.parse(text) as string
  } catch {
    return escapeHtml(text).replace(/\n/g, '<br>')
  }
}

export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

export function formatTimestamp(ts: string): string {
  if (!ts) return ''
  if (/^\d{2}:\d{2}$/.test(ts)) return ts
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts
  const now = new Date()
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (d.toDateString() === now.toDateString()) return time
  const sameYear = d.getFullYear() === now.getFullYear()
  const dateStr = d.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
  })
  return `${dateStr}, ${time}`
}
