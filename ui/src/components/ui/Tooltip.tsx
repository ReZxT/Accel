interface Props {
  text: string
  side?: 'right' | 'top' | 'bottom'
  children: React.ReactNode
}

export default function Tooltip({ text, side = 'right', children }: Props) {
  const pos =
    side === 'right'
      ? 'left-full ml-2.5 top-1/2 -translate-y-1/2'
      : side === 'top'
      ? 'bottom-full mb-2 left-1/2 -translate-x-1/2'
      : 'top-full mt-2 left-1/2 -translate-x-1/2'

  return (
    <div className="relative group/tip">
      {children}
      <span
        className={`absolute ${pos} z-50 pointer-events-none whitespace-nowrap rounded-md bg-zinc-800/90 backdrop-blur-sm px-2 py-1 text-xs text-text-primary opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150`}
      >
        {text}
      </span>
    </div>
  )
}
