import { fmt } from '../components/format'
import Info from '../components/Info'
import { useI18n } from '../i18n'
import { useExplain } from '../i18n/explain'
import { digitsFor } from '../map/scales'
import type { ResolvedLayer } from '../state/MapLink'

/** Says what the map colours mean and lets you step through the years. */
export default function MapLegend({ layer, years, year, setYear, loading }: {
  layer: ResolvedLayer | null
  years: string[] | null
  year: string | null
  setYear: (y: string) => void
  loading: boolean
}) {
  const { t } = useI18n()
  const x = useExplain()
  if (!layer) return loading ? <div className="legend"><span className="muted small">{t('loadingMap')}</span></div> : null
  const s = layer.scale
  const nd = digitsFor(s.max)
  const i = years && year ? years.indexOf(year) : -1
  return (
    <div className="legend">
      <div className="legend-title">
        <span className="legend-kicker">{t('onMap')}</span>
        <b>{layer.label}</b> <Info>{s.discrete ? x.procurement.choropleth : x.general.mapLegend}</Info>
      </div>
      {years && years.length > 1 && i >= 0 && (
        <div className="legend-year">
          <button type="button" disabled={i <= 0} onClick={() => setYear(years[i - 1])} aria-label="Previous year">‹</button>
          <input type="range" min={0} max={years.length - 1} step={1} value={i} onChange={(e) => setYear(years[Number(e.target.value)])} aria-label={t('year')} />
          <button type="button" disabled={i >= years.length - 1} onClick={() => setYear(years[i + 1])} aria-label="Next year">›</button>
          <b className="legend-year-value">{year}</b>
        </div>
      )}
      {s.discrete
        ? <div className="legend-blocks">{s.stops.map((c) => <i key={c} style={{ background: c }} />)}</div>
        : <div className="legend-bar" style={{ background: `linear-gradient(to right, ${s.stops.join(', ')})` }} />}
      <div className="legend-ends">
        <span>{s.discrete ? t('legendLow') : fmt(s.min, nd)}</span>
        <span className="muted">{s.discrete ? '' : layer.unit}</span>
        <span>{s.discrete ? t('legendHigh') : fmt(s.max, nd)}</span>
      </div>
    </div>
  )
}
