import type { Soil } from '../../api/types'
import Card from '../../components/Card'
import { fmt } from '../../components/format'
import Info from '../../components/Info'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'

const ORDER = ['soc', 'phh2o', 'clay', 'sand', 'silt', 'nitrogen', 'bdod', 'cec']

export default function SoilCard({ soil, kind }: { soil: Soil; kind: 'county' | 'commune' }) {
  const { t } = useI18n()
  const x = useExplain()
  const v = soil.values
  if (!v) return null
  const ph = v.phh2o?.median
  return (
    <Card
      title={t('soil')}
      sub={<>{t('soilSub')} <Info>{x.soil.range}</Info></>}
      right={v.texture && <span className="nowrap"><span className="pill">{t('texture')}: {v.texture}</span> <Info>{x.soil.texture}</Info></span>}
    >
      <div className="soil-grid">
        {ORDER.map((p) => {
          const s = v[p] as { median: number; p10: number; p90: number } | null
          const meta = soil.properties[p]
          if (!s || !meta) return null
          return (
            <div key={p} className="soil-cell">
              <div className="muted small">{meta.label} <Info>{x.soil[p as keyof typeof x.soil]}</Info></div>
              <div className="big">{fmt(s.median, p === 'phh2o' || p === 'bdod' || p === 'nitrogen' ? 2 : 1)} <span className="muted small">{meta.unit}</span></div>
              <div className="muted small">{fmt(s.p10, 1)} – {fmt(s.p90, 1)}</div>
            </div>
          )
        })}
      </div>
      {ph !== undefined && ph < 6 && <p className="note warn">{t('acidic')}</p>}
      <SourceNote source={soil.source} period={soil.depth} resolution={soil.resolution} confidence={soil.confidence[kind]} note={soil.confidence.note} />
    </Card>
  )
}
