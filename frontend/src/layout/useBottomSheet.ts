import { useCallback, useEffect, useLayoutEffect, useRef, useState, type PointerEvent as RPointerEvent } from 'react'

const PHONE = '(max-width: 900px)'

export function useIsPhone(): boolean {
  const [phone, setPhone] = useState(() => typeof window !== 'undefined' && window.matchMedia(PHONE).matches)
  useEffect(() => {
    const m = window.matchMedia(PHONE)
    const on = () => setPhone(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return phone
}

/**
 * Phone layout: the data panel is a bottom sheet over the full-screen map. Closed, only its
 * header (the "peek") shows; tap or drag the header up to open it, drag it down or tap to
 * close. The content scrolls inside the open sheet. Desktop: does nothing.
 */
export function useBottomSheet(phone: boolean) {
  const [open, setOpen] = useState(false)
  const sheet = useRef<HTMLElement | null>(null)
  const head = useRef<HTMLElement | null>(null)
  const drag = useRef<{ y0: number; base: number; max: number; moved: boolean; id: number } | null>(null)

  // peek height = header height (it changes with the section intro text)
  useLayoutEffect(() => {
    const el = sheet.current
    const h = head.current
    if (!phone || !el || !h) return
    const set = () => document.documentElement.style.setProperty('--peek', `${h.offsetHeight}px`)
    set()
    const ro = new ResizeObserver(set)
    ro.observe(h)
    return () => ro.disconnect()
  }, [phone])

  const closedOffset = () => {
    const el = sheet.current
    const h = head.current
    return el && h ? Math.max(0, el.offsetHeight - h.offsetHeight) : 0
  }

  const onPointerDown = useCallback((e: RPointerEvent<HTMLElement>) => {
    if (!phone || (e.target as HTMLElement).closest('button, a, input, select, textarea')) return
    const max = closedOffset()
    drag.current = { y0: e.clientY, base: open ? 0 : max, max, moved: false, id: e.pointerId }
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [phone, open])

  const onPointerMove = useCallback((e: RPointerEvent<HTMLElement>) => {
    const d = drag.current
    const el = sheet.current
    if (!d || !el || e.pointerId !== d.id) return
    const dy = e.clientY - d.y0
    if (Math.abs(dy) > 6) d.moved = true
    if (!d.moved) return
    const y = Math.min(d.max, Math.max(0, d.base + dy))
    el.style.transition = 'none'
    el.style.transform = `translateY(${y}px)`
  }, [])

  const onPointerUp = useCallback((e: RPointerEvent<HTMLElement>) => {
    const d = drag.current
    const el = sheet.current
    drag.current = null
    if (!d || !el) return
    el.style.transition = ''
    el.style.transform = ''
    if (!d.moved) {
      setOpen((o) => !o) // tap toggles
      return
    }
    const dy = e.clientY - d.y0
    // follow the swipe direction once it is clear, otherwise snap to the nearer end
    if (Math.abs(dy) > 40) setOpen(dy < 0)
    else setOpen(d.base + dy < d.max / 2)
  }, [])

  useEffect(() => {
    if (!phone) setOpen(false)
  }, [phone])

  return {
    open: phone && open,
    setOpen,
    sheetRef: sheet,
    headRef: head,
    headHandlers: phone ? { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp } : {},
  }
}
