import type { ReactNode } from 'react'

export default function Card({ title, sub, right, children, className = '' }: {
  title: ReactNode
  sub?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      <header className="card-head">
        <div>
          <h3>{title}</h3>
          {sub && <p className="muted small">{sub}</p>}
        </div>
        {right}
      </header>
      {children}
    </section>
  )
}
