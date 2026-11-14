import { useState, type ReactNode } from 'react'
import Info from './Info'

function stored(id: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(`s2f.open.${id}`)
    return v === null ? fallback : v === '1'
  } catch {
    return fallback
  }
}

/** Open/close panel. Its content is only rendered while open; the state is remembered. */
export default function Collapsible({ id, title, info, summary, defaultOpen = false, children }: {
  id: string
  title: ReactNode
  info?: ReactNode
  /** Short text shown on the right of the header (useful while closed). */
  summary?: ReactNode
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(() => stored(id, defaultOpen))
  const toggle = () => {
    setOpen((o) => {
      try {
        localStorage.setItem(`s2f.open.${id}`, o ? '0' : '1')
      } catch {
        /* storage unavailable */
      }
      return !o
    })
  }
  return (
    <section className={`clp ${open ? 'open' : ''}`}>
      <div className="clp-head">
        <button type="button" className="clp-toggle" aria-expanded={open} onClick={toggle}>
          <svg className="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <span>{title}</span>
        </button>
        {info && <Info>{info}</Info>}
        {summary && <span className="clp-summary">{summary}</span>}
      </div>
      {open && <div className="clp-body">{children}</div>}
    </section>
  )
}
