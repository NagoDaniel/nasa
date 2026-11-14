import type { AgroYearly } from '../../api/types'
import Card from '../../components/Card'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'

const ROWS = [
  'heat35_jul_aug', 'heat32_jul_aug', 'heat30_jun', 'rootmoist_jja_z', 'dry_spell_apr_sep',
  'rain_flowering_small_grain', 'wet_days_flowering_small_grain', 'late_frost',
  'rain_harvest_small_grain', 'rain_harvest_summer_crops',
]

export default function SeasonEvents({ agro, kind }: { agro: AgroYearly; kind: 'county' | 'commune' }) {
  const { t } = useI18n()
  const rows = ROWS.filter((k) => agro.indicators[k] && agro.values[k])
  const hit = (k: string, v: number | null) => {
    const h = agro.hazards[k]
    if (!h || v === null) return false
    return h.op === '>=' ? v >= h.threshold : v <= h.threshold
  }
  return (
    <Card title={t('seasonEvents')} sub={t('seasonEventsSub')}>
      <div className="table-scroll">
        <table className="events">
          <thead>
            <tr>
              <th />
              {agro.years.map((y) => <th key={y}>{String(y).slice(2)}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => {
              const meta = agro.indicators[k]
              return (
                <tr key={k}>
                  <th title={`${meta.why}\n${agro.hazards[k]?.text ?? ''}`}>
                    {meta.label}
                    <span className="muted"> · {agro.hazards[k]?.text}</span>
                  </th>
                  {agro.values[k].map((v, i) => (
                    <td key={i} className={hit(k, v) ? 'hit' : ''} title={`${agro.years[i]}: ${fmt(v, 1)} ${meta.unit}`}>
                      {fmt(v, k === 'rootmoist_jja_z' ? 1 : 0)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <SourceNote
        source="NASA POWER daily (MERRA-2) · NASA GLDAS Noah 2.1 monthly"
        period={`${agro.years[0]}–${agro.years[agro.years.length - 1]}`}
        confidence={agro.confidence[kind]}
        note={agro.confidence.note}
        assumptions={['Heat thresholds are physiological; rain, wet-day and dry-spell thresholds sit near the regional 75th percentile of 2015–2025 (an unusually wet / dry year for the region).']}
      />
    </Card>
  )
}
