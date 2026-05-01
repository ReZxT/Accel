interface Props {
  path?: string
}
export default function NotesPanel({ path }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center text-text-tertiary text-sm">
      Notes — coming in Task 9{path ? `: ${path}` : ''}
    </div>
  )
}
