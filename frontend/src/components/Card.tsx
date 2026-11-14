import type { ReactNode } from 'react'
import Info from './Info'

export default function Card({ title, sub, right, info, children, className = '' }: {
  title: ReactNode
  sub?: ReactNode
  right?: ReactNode
  /** Explanation shown behind an ⓘ button next to the title. */
  info?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      <header className="card-head">
        <div>
          <h3>{title}{info && <> <Info>{info}</Info></>}</h3>
          {sub && <p className="muted small">{sub}</p>}
        </div>
        {right}
      </header>
      {children}
    </section>
  )
}
