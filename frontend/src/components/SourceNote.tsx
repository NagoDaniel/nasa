import { useI18n } from '../i18n'

type Props = {
  source: string
  period?: string
  resolution?: string
  confidence?: string
  note?: string
  assumptions?: string[]
  extra?: string
}

export function ConfidenceBadge({ level }: { level: string }) {
  const { t } = useI18n()
  const key = `conf_${level}` as Parameters<typeof t>[0]
  return <span className={`badge conf-${level}`}>{t('confidence')}: {t(key)}</span>
}

/** The transparency footer every result carries (requirement 10). */
export default function SourceNote({ source, period, resolution, confidence, note, assumptions, extra }: Props) {
  const { t } = useI18n()
  return (
    <div className="source-note">
      <div>
        <b>{t('source')}:</b> {source}
      </div>
      {(period || resolution) && (
        <div>
          {period && <><b>{t('period')}:</b> {period} </>}
          {resolution && <><b>{t('resolution')}:</b> {resolution}</>}
        </div>
      )}
      {confidence && (
        <div>
          <ConfidenceBadge level={confidence} /> {note && <span className="muted">{note}</span>}
        </div>
      )}
      {extra && <div className="muted">{extra}</div>}
      {assumptions && assumptions.length > 0 && (
        <details>
          <summary>{t('assumptions')}</summary>
          <ul>{assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        </details>
      )}
    </div>
  )
}
