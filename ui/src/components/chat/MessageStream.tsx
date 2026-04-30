import { useRef, useEffect } from 'react'
import { useChatStore } from '../../stores/chatStore'
import MessageItem from './MessageItem'
import ToolCallBlock from './blocks/ToolCallBlock'
import ToolResultBlock from './blocks/ToolResultBlock'
import ApprovalBlock from './blocks/ApprovalBlock'
import { formatMarkdown } from '../../lib/format'

export default function MessageStream() {
  const messages = useChatStore((s) => s.messages)
  const isLoading = useChatStore((s) => s.isLoading)
  const streamingText = useChatStore((s) => s.streamingText)
  const streamingThinking = useChatStore((s) => s.streamingThinking)
  const streamingTools = useChatStore((s) => s.streamingTools)
  const streamingResults = useChatStore((s) => s.streamingResults)
  const streamingApprovals = useChatStore((s) => s.streamingApprovals)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText, streamingTools, streamingResults, streamingApprovals])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-accent mb-2">Accel</h1>
          <p className="text-sm text-text-tertiary max-w-sm">
            Your second brain. Ask anything, build anything, remember everything.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {messages.map((msg, i) => (
        <MessageItem key={`${msg.timestamp}-${i}`} message={msg} />
      ))}

      {isLoading && (
        <div className="px-4 py-3">
          <div className="max-w-3xl mx-auto flex gap-3">
            <div className="flex-shrink-0 mt-1">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
            </div>
            <div className="min-w-0 flex-1">
              {streamingThinking && (
                <div className="text-xs text-orange-400/80 italic border-l-2 border-orange-400/40 pl-2 mb-2">
                  Thinking...
                </div>
              )}

              {streamingTools.map((tc) => (
                <ToolCallBlock key={tc.id} tool={tc.tool} args={tc.args} />
              ))}
              {streamingResults.map((tr) => (
                <ToolResultBlock key={tr.id} tool={tr.tool} output={tr.output} image={tr.image} mime_type={tr.mime_type} />
              ))}
              {streamingApprovals.map((a) => (
                <ApprovalBlock key={a.request_id} approval={a} />
              ))}

              {streamingText ? (
                <div
                  className="text-sm leading-relaxed [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:text-[13px] [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-blue-400 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(streamingText) }}
                />
              ) : (
                !streamingTools.length && (
                  <div className="flex gap-1 py-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.15s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-bounce [animation-delay:0.3s]" />
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
