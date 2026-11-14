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

export function ConfidenceBadge({ level, info = true, short = false }: { level: string; info?: boolean; short?: boolean }) {
  const { t } = useI18n()
  const x = useExplain()
  const key = `conf_${level}` as Parameters<typeof t>[0]
  return (
    <span className="nowrap">
      <span className={`badge conf-${level}`}>{short ? t(key) : `${t('confidence')}: ${t(key)}`}</span>
      {info && <> <Info>{x.general.confidence}</Info></>}
    </span>
  )
}

/**
 * Transparency footer every result carries (requirement 10): the confidence is
 * always visible, source / period / resolution / assumptions open on demand.
 */
export default function SourceNote({ source, period, resolution, confidence, note, assumptions, extra }: Props) {
  const { t } = useI18n()
  const x = useExplain()
  return (
    <div className="source-note">
      {confidence && <ConfidenceBadge level={confidence} />}
      <details>
        <summary>{t('sourceDetails')}</summary>
        <div className="source-body">
          <div><b>{t('source')}:</b> {source}</div>
          {period && <div><b>{t('period')}:</b> {period} <Info>{x.general.period}</Info></div>}
          {resolution && <div><b>{t('resolution')}:</b> {resolution} <Info>{x.general.resolution}</Info></div>}
          {note && <div>{note}</div>}
          {extra && <div>{extra}</div>}
          {assumptions && assumptions.length > 0 && (
            <div>
              <b>{t('assumptions')}:</b>
              <ul>{assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            </div>
          )}
        </div>
      </details>
    </div>
  )
}
