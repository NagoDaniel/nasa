import type { AgroYearly } from '../../api/types'
import { fmt } from '../../components/format'
import Info from '../../components/Info'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { useMapLink } from '../../state/MapLink'

export const RISK_ROWS = [
  'heat35_jul_aug', 'heat32_jul_aug', 'heat30_jun', 'rootmoist_jja_z', 'dry_spell_apr_sep',
  'rain_flowering_small_grain', 'wet_days_flowering_small_grain', 'late_frost',
  'rain_harvest_small_grain', 'rain_harvest_summer_crops',
]

export function isHit(agro: AgroYearly, k: string, v: number | null) {
  const h = agro.hazards[k]
  if (!h || v === null || v === undefined) return false
  return h.op === '>=' ? v >= h.threshold : v <= h.threshold
}

/** Hazard table. Click a row (or a cell) to colour the map by that hazard (and year). */
export default function SeasonEvents({ agro, kind, selected, onSelect }: {
  agro: AgroYearly
  kind: 'county' | 'commune'
  selected: string
  onSelect: (key: string) => void
}) {
  const { t } = useI18n()
  const x = useExplain()
  const { year, setYear } = useMapLink()
  const rows = RISK_ROWS.filter((k) => agro.indicators[k] && agro.values[k])
  return (
    <div className="block">
      <div className="table-scroll">
        <table className="events">
          <thead>
            <tr>
              <th>{t('seasonEvents')} <Info>{x.general.eventsTable}</Info></th>
              {agro.years.map((y) => <th key={y} className={String(y) === year ? 'col-on' : ''}>{String(y).slice(2)}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => {
              const meta = agro.indicators[k]
              const on = k === selected
              return (
                <tr key={k} className={on ? 'row-on' : ''} onClick={() => onSelect(k)}>
                  <th>
                    <span className="row-label">{meta.label}</span> <Info>{x.agro[k] ?? `${meta.why} ${agro.hazards[k]?.text ?? ''}`}</Info>
                  </th>
                  {agro.values[k].map((v, i) => (
                    <td
                      key={i}
                      className={`${isHit(agro, k, v) ? 'hit' : ''} ${on && String(agro.years[i]) === year ? 'cell-on' : ''}`}
                      title={`${agro.years[i]}: ${fmt(v, 1)} ${meta.unit}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelect(k)
                        setYear(String(agro.years[i]))
                      }}
                    >
                      {fmt(v, k === 'rootmoist_jja_z' ? 1 : 0)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="hint">{t('hintRow')}</p>
      <SourceNote
        source="NASA POWER daily (MERRA-2) · NASA GLDAS Noah 2.1 monthly"
        period={`${agro.years[0]}–${agro.years[agro.years.length - 1]}`}
        confidence={agro.confidence[kind]}
        note={agro.confidence.note}
        assumptions={[
          ...rows.map((k) => `${agro.indicators[k].label}: ${agro.hazards[k]?.text ?? ''}`),
          'Heat thresholds are physiological; rain, wet-day and dry-spell thresholds sit near the regional 75th percentile of 2015–2025 (an unusually wet / dry year for the region).',
        ]}
      />
    </div>
  )
}
