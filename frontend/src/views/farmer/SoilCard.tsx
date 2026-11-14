import type { Soil, Terrain } from '../../api/types'
import Card from '../../components/Card'
import { fmt } from '../../components/format'
import Info from '../../components/Info'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'

const ORDER = ['soc', 'phh2o', 'clay', 'sand', 'silt', 'nitrogen', 'bdod', 'cec']

export default function SoilCard({ soil, terrain, kind }: { soil: Soil; terrain: Terrain | null; kind: 'county' | 'commune' }) {
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
      {terrain && <TerrainRows tr={terrain} kind={kind} />}
    </Card>
  )
}

function TerrainRows({ tr, kind }: { tr: Terrain; kind: 'county' | 'commune' }) {
  const v = tr.values
  const lc = v.landcover_pct ?? {}
  const cells: [string, string][] = []
  if (v.elevation_m !== undefined) cells.push(['Mean elevation', `${fmt(v.elevation_m, 0)} m`])
  if (v.cropland_slope_pct !== undefined) cells.push(['Cropland slope (mean)', `${fmt(v.cropland_slope_pct, 1)} %`])
  if (v.cropland_steep_share_pct !== undefined) cells.push([`Cropland ≥ ${tr.steep_threshold_pct} % slope`, `${fmt(v.cropland_steep_share_pct, 1)} %`])
  if (lc['40'] !== undefined) cells.push(['Cropland share', `${fmt(lc['40'], 1)} %`])
  if (lc['30'] !== undefined) cells.push(['Grassland share', `${fmt(lc['30'], 1)} %`])
  if (lc['10'] !== undefined) cells.push(['Tree cover share', `${fmt(lc['10'], 1)} %`])
  if (!cells.length) return null
  return (
    <>
      <div className="soil-grid">
        {cells.map(([label, val]) => (
          <div key={label} className="soil-cell">
            <div className="muted small">{label}</div>
            <div className="big">{val}</div>
          </div>
        ))}
      </div>
      <SourceNote
        source={`${tr.sources.terrain}; ${tr.sources.landcover}`}
        period="SRTM 2000 · WorldCover 2021"
        resolution={`${tr.resolution.terrain} / ${tr.resolution.landcover}`}
        confidence={tr.confidence[kind]}
        note={tr.confidence.note}
      />
    </>
  )
}
