import { useState, useCallback } from 'react'
import type { Message } from '../../types'
import { formatMarkdown, formatTimestamp } from '../../lib/format'
import ThinkingBlock from './blocks/ThinkingBlock'

interface Props {
  message: Message
}

export default function MessageItem({ message }: Props) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [message.content])

  return (
    <div className={`px-4 py-3 ${isUser ? 'bg-white/[0.02]' : ''}`}>
      <div className="max-w-3xl mx-auto flex gap-3">
        {/* Role indicator */}
        <div className="flex-shrink-0 mt-1">
          <div
            className={`w-2 h-2 rounded-full ${
              isUser ? 'bg-accent' : 'bg-success'
            }`}
          />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          {message.thoughts && <ThinkingBlock content={message.thoughts} />}
          <div
            className="text-sm leading-relaxed prose-invert [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_a]:no-underline [&_a:hover]:text-blue-300 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
            dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
          />

          {/* Meta row */}
          <div className="flex items-center gap-3 mt-2 text-xs text-text-tertiary">
            <span>{formatTimestamp(message.timestamp)}</span>
            <button
              onClick={handleCopy}
              className="hover:text-text-secondary transition-colors"
              title="Copy"
            >
              {copied ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
