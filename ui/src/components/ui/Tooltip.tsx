import { useState, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  text: string
  side?: 'right' | 'top'
  disabled?: boolean
  children: React.ReactNode
}

export default function Tooltip({ text, side = 'right', disabled = false, children }: Props) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const ref = useRef<HTMLDivElement>(null)

  const show = useCallback(() => {
    if (!ref.current) return
    const r = ref.current.getBoundingClientRect()
    if (side === 'right') setPos({ x: r.right + 8, y: r.top + r.height / 2 })
    else setPos({ x: r.left + r.width / 2, y: r.top - 8 })
    setVisible(true)
  }, [side])

  const hide = useCallback(() => setVisible(false), [])

  if (disabled) return <>{children}</>

  return (
    <div ref={ref} onMouseEnter={show} onMouseLeave={hide}>
      {children}
      {visible && createPortal(
        <span
          style={{
            position: 'fixed',
            left: side === 'right' ? pos.x : pos.x,
            top: pos.y,
            transform: side === 'right' ? 'translateY(-50%)' : 'translate(-50%, -100%)',
            zIndex: 9999,
          }}
          className="pointer-events-none whitespace-nowrap rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-200 shadow-lg"
        >
          {text}
        </span>,
        document.body
      )}
    </div>
  )
}
