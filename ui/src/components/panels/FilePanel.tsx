import { formatMarkdown } from '../../lib/format'

interface Props {
  path?: string
  content?: string
}

function isImagePath(path: string) {
  return /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(path)
}

function isBase64Image(content: string) {
  return content.startsWith('data:image/')
}

export default function FilePanel({ path, content }: Props) {
  if (!path && !content) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
        No file selected
      </div>
    )
  }

  // Image via URL or base64
  if ((path && isImagePath(path)) || (content && isBase64Image(content))) {
    const src = content ?? path!
    return (
      <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
        <img src={src} alt={path ?? 'image'} className="max-w-full max-h-full rounded-md object-contain" />
      </div>
    )
  }

  // Markdown
  if (path?.endsWith('.md') && content) {
    return (
      <div
        className="flex-1 p-4 overflow-auto text-sm leading-relaxed prose-invert [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mb-3 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:bg-black/40 [&_pre]:border [&_pre]:border-border [&_pre]:rounded-md [&_pre]:p-3 [&_code]:font-mono [&_code]:text-[13px] [&_code]:bg-white/[0.06] [&_code]:px-1.5 [&_code]:rounded"
        dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }}
      />
    )
  }

  // Code / plain text
  return (
    <div className="flex-1 overflow-auto p-4">
      <pre className="text-xs font-mono text-text-secondary whitespace-pre-wrap break-words leading-relaxed">
        {content ?? `Path: ${path}`}
      </pre>
    </div>
  )
}
