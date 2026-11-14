import type { Soil } from '../../api/types'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import StatTile from '../../components/StatTile'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'

const ORDER = ['phh2o', 'soc', 'clay', 'sand', 'silt', 'nitrogen', 'bdod', 'cec']

/** Soil properties as tiles. Click one to colour the map by it (soil differs commune by commune). */
export default function SoilCard({ soil, kind, selected, onSelect }: {
  soil: Soil
  kind: 'county' | 'commune'
  selected: string
  onSelect: (prop: string) => void
}) {
  const { t } = useI18n()
  const x = useExplain()
  const v = soil.values
  if (!v) return null
  const ph = v.phh2o?.median
  return (
    <div className="block">
      {v.texture && <p className="lead">{t('texture')}: <b>{v.texture}</b></p>}
      <div className="tiles">
        {ORDER.map((p) => {
          const s = v[p] as { median: number; p10: number; p90: number } | null
          const meta = soil.properties[p]
          if (!s || !meta) return null
          const nd = p === 'phh2o' || p === 'bdod' || p === 'nitrogen' ? 2 : 1
          return (
            <StatTile
              key={p}
              label={meta.label}
              value={fmt(s.median, nd)}
              unit={meta.unit === 'pH' ? '' : meta.unit}
              note={`${fmt(s.p10, 1)} – ${fmt(s.p90, 1)}`}
              info={<>{x.soil[p as keyof typeof x.soil]}<br /><br />{x.soil.range}</>}
              active={selected === p}
              onClick={() => onSelect(p)}
            />
          )
        })}
      </div>
      {ph !== undefined && ph < 6 && <p className="note warn">{t('acidic')}</p>}
      <p className="hint">{t('hintTile')}</p>
      <SourceNote source={soil.source} period={soil.depth} resolution={soil.resolution} confidence={soil.confidence[kind]} note={soil.confidence.note} />
    </div>
  )
}
