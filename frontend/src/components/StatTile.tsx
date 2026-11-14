import type { ReactNode } from 'react'
import { useI18n } from '../i18n'
import Info from './Info'

/** One headline number. Clicking it colours the map by that number. */
export default function StatTile({ label, value, unit, note, tone = 'neutral', info, active = false, onClick }: {
  label: ReactNode
  value: ReactNode
  unit?: string
  note?: ReactNode
  tone?: 'neutral' | 'good' | 'warn' | 'bad'
  info?: ReactNode
  active?: boolean
  onClick?: () => void
}) {
  const { t } = useI18n()
  return (
    <div
      className={`tile ${active ? 'on' : ''} ${onClick ? 'clickable' : ''}`}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-pressed={onClick ? active : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
          e.preventDefault()
          onClick()
        }
      }}
    >
      <div className="tile-label">{label} {info && <Info>{info}</Info>}</div>
      <div className="tile-value">{value}{unit && <span className="tile-unit"> {unit}</span>}</div>
      {note && <div className={`tile-note tone-${tone}`}>{note}</div>}
      {active && <div className="tile-flag">{t('onMap')}</div>}
    </div>
  )
}
