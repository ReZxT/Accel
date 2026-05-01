interface Props {
  path?: string
  content?: string
}
export default function FilePanel({ path, content }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      {path ?? content ?? 'No file selected'}
    </div>
  )
}
