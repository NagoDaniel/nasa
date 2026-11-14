import type { AreaBundle, CropMap } from '../../api/types'
import Card from '../../components/Card'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'

// EUCROPMAP code -> INS crop id (for the county cross-check)
const INS_ID: Record<string, string> = { '216': 'maize', '211': 'wheat', '213': 'barley', '215': 'oats', '231': 'sunflower', '233': 'soy', '232': 'rapeseed', '240': 'grain_legumes' }
const YEAR_IDX: Record<string, number> = { '2018': 3, '2022': 7 }

export default function CropMixCard({ cm, stats, kind }: { cm: CropMap; stats: AreaBundle['crop_stats']; kind: 'county' | 'commune' }) {
  const { lang } = useI18n()
  const v = cm.values
  if (!v) return null
  const years = cm.years.filter((y) => v[y])
  const last = years[years.length - 1]
  const arable = (y: string) => Object.entries(v[y] ?? {}).filter(([c]) => +c >= 200 && +c < 300)
  const total = (y: string) => arable(y).reduce((s, [, n]) => s + n, 0)
  const top = arable(last).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([c]) => c)
  const max = Math.max(...years.flatMap((y) => top.map((c) => v[y]?.[c] ?? 0)), 1)
  const legume = (y: string) => ((v[y]?.['240'] ?? 0) + (v[y]?.['233'] ?? 0)) / (total(y) || 1)

  return (
    <Card
      title={lang === 'ro' ? 'Structura culturilor (hartă satelitară)' : 'Crop mix (satellite crop map)'}
      sub={lang === 'ro' ? 'Hectare pe cultură, teren arabil' : 'Hectares per crop on arable land'}
      right={<span className="pill">{lang === 'ro' ? 'Leguminoase' : 'Legumes'}: {years.map((y) => `${y} ${fmt(100 * legume(y), 1)}%`).join(' → ')}</span>}
    >
      <table className="mix">
        <thead>
          <tr>
            <th />
            {years.map((y) => <th key={y}>{y}</th>)}
            {kind === 'county' && <th className="muted">INS {years.join(' / ')}</th>}
          </tr>
        </thead>
        <tbody>
          {top.map((c) => (
            <tr key={c}>
              <td>{cm.classes[c]}</td>
              {years.map((y) => (
                <td key={y}>
                  <div className="hbar"><i style={{ width: `${(100 * (v[y]?.[c] ?? 0)) / max}%` }} /></div>
                  <span className="small">{fmt(v[y]?.[c] ?? 0)} ha · {fmt((100 * (v[y]?.[c] ?? 0)) / (total(y) || 1))}%</span>
                </td>
              ))}
              {kind === 'county' && (
                <td className="muted small">
                  {INS_ID[c] ? years.map((y) => fmt(stats.values[INS_ID[c]]?.area_ha?.[YEAR_IDX[y]] ?? null)).join(' / ') : '–'}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <SourceNote
        source={cm.source}
        resolution={cm.resolution}
        confidence={cm.confidence[kind]}
        note={cm.confidence.note}
        extra={kind === 'county' ? 'County totals can differ from INS statistics by 30–50% for some crops; use INS for volumes and the map for the crop mix of communes.' : undefined}
      />
    </Card>
  )
}
