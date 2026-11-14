import { useI18n } from '../i18n'
import { useExplain } from '../i18n/explain'
import Info from './Info'

type Props = {
  source: string
  period?: string
  resolution?: string
  confidence?: string
  note?: string
  assumptions?: string[]
  extra?: string
}

export function ConfidenceBadge({ level, info = true }: { level: string; info?: boolean }) {
  const { t } = useI18n()
  const x = useExplain()
  const key = `conf_${level}` as Parameters<typeof t>[0]
  return (
    <span className="nowrap">
      <span className={`badge conf-${level}`}>{t('confidence')}: {t(key)}</span>
      {info && <> <Info>{x.general.confidence}</Info></>}
    </span>
  )
}

/** The transparency footer every result carries (requirement 10). */
export default function SourceNote({ source, period, resolution, confidence, note, assumptions, extra }: Props) {
  const { t } = useI18n()
  const x = useExplain()
  return (
    <div className="source-note">
      <div>
        <b>{t('source')}:</b> {source}
      </div>
      {(period || resolution) && (
        <div>
          {period && <><b>{t('period')}:</b> {period} <Info>{x.general.period}</Info> </>}
          {resolution && <><b>{t('resolution')}:</b> {resolution} <Info>{x.general.resolution}</Info></>}
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
