import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../i18n'

// Only one explanation is open at a time: opening one closes the previous.
let closeOpen: (() => void) | null = null

/**
 * Small ⓘ button that explains a number. Opens on hover, keyboard focus or tap
 * (tap pins it open on phones). Rendered in a portal so tables with overflow
 * scrolling can't clip it.
 */
export default function Info({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const { lang } = useI18n()
  const id = useId()
  const btn = useRef<HTMLButtonElement>(null)
  const tip = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const hideTimer = useRef<number | undefined>(undefined)

  const closeNow = useCallback(() => {
    window.clearTimeout(hideTimer.current)
    setOpen(false)
    setPinned(false)
  }, [])
  const show = () => {
    window.clearTimeout(hideTimer.current)
    if (closeOpen && closeOpen !== closeNow) closeOpen()
    closeOpen = closeNow
    setOpen(true)
  }
  const hide = useCallback(() => {
    hideTimer.current = window.setTimeout(() => {
      setOpen(false)
      setPinned(false)
    }, 120)
  }, [])

  // Place below the button (above if there is no room), clamped to the viewport.
  useLayoutEffect(() => {
    if (!open || !btn.current || !tip.current) return
    const b = btn.current.getBoundingClientRect()
    const t = tip.current.getBoundingClientRect()
    const m = 8
    let left = b.left + b.width / 2 - t.width / 2
    left = Math.max(m, Math.min(left, window.innerWidth - t.width - m))
    let top = b.bottom + 6
    if (top + t.height > window.innerHeight - m) top = Math.max(m, b.top - t.height - 6)
    setPos({ top, left })
  }, [open, children])

  useEffect(() => {
    if (!open) return
    const close = () => {
      setOpen(false)
      setPinned(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    const onDown = (e: PointerEvent) => {
      const n = e.target as Node
      if (!btn.current?.contains(n) && !tip.current?.contains(n)) close()
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onDown)
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onDown)
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
    }
  }, [open])

  useEffect(() => () => {
    window.clearTimeout(hideTimer.current)
    if (closeOpen === closeNow) closeOpen = null
  }, [closeNow])

  return (
    <>
      <button
        ref={btn}
        type="button"
        className={`info-btn ${open ? 'on' : ''}`}
        aria-label={lang === 'ro' ? 'Ce înseamnă?' : 'What does this mean?'}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onMouseEnter={show}
        onMouseLeave={() => !pinned && hide()}
        onFocus={show}
        onBlur={() => !pinned && hide()}
        onClick={(e) => {
          e.stopPropagation()
          if (pinned) {
            setPinned(false)
            setOpen(false)
          } else {
            setPinned(true)
            show()
          }
        }}
      >
        i
      </button>
      {open &&
        createPortal(
          <div
            ref={tip}
            id={id}
            role="tooltip"
            className={`info-tip ${wide ? 'wide' : ''}`}
            style={pos ? { top: pos.top, left: pos.left } : { top: -9999, left: -9999 }}
            onMouseEnter={show}
            onMouseLeave={() => !pinned && hide()}
          >
            {children}
          </div>,
          document.body,
        )}
    </>
  )
}
