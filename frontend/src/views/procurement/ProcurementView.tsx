import { useEffect, useMemo, useRef, useState } from 'react'
import { getProcurement } from '../../api/client'
import type { ProcurementResponse } from '../../api/types'
import Chart, { PALETTE, type ChartOption } from '../../components/Chart'
import Collapsible from '../../components/Collapsible'
import { fmt, scoreColor } from '../../components/format'
import Info from '../../components/Info'
import { ConfidenceBadge } from '../../components/SourceNote'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { B_CROPS, cropName } from '../../i18n/names'
import { makeScale } from '../../map/scales'
import { useMapLink } from '../../state/MapLink'
import type { ProcurementSection } from '../../state/sections'

export type Metric = 'availability' | 'quality' | 'impact'
const METRICS: Metric[] = ['availability', 'quality', 'impact']
const SCORE_SCALE = makeScale([], 'score')

const HAZARD_SHORT: Record<string, string> = {
  heat35_jul_aug: 'heat ≥35 °C', heat32_jul_aug: 'hot summer', heat30_jun: 'June heat', rootmoist_jja_z: 'dry soil',
  dry_spell_apr_sep: 'dry spell', rain_flowering_small_grain: 'wet flowering', wet_days_flowering_small_grain: 'wet flowering',
  late_frost: 'late frost', rain_harvest_small_grain: 'wet harvest', rain_harvest_summer_crops: 'wet harvest',
}

/** Buyer's view. The crop and score chosen here colour the counties on the map. */
export default function ProcurementView({ section, selectedCounty, active }: {
  section: ProcurementSection
  selectedCounty: string | null
  active: boolean
}) {
  const { t, lang } = useI18n()
  const { setCustomLayer, command } = useMapLink()
  const [crop, setCrop] = useState('maize')
  const [metric, setMetric] = useState<Metric>('availability')

  // Assistant: pick the ingredient crop (and score) shown here.
  const applied = useRef(0)
  useEffect(() => {
    if (!command || command.type !== 'procurement' || command.seq === applied.current) return
    applied.current = command.seq
    setCrop(command.crop)
    if (command.metric) setMetric(command.metric)
  }, [command])
  const res = useAsync(crop, () => getProcurement(crop))
  const d = res.data && res.data.crop === crop ? res.data : null

  useEffect(() => {
    if (!active) return
    if (!d) return setCustomLayer(null)
    setCustomLayer({
      label: `${cropName(crop, lang)}: ${t(metric)}`,
      unit: t('scoreUnit'),
      values: Object.fromEntries(Object.entries(d.counties).map(([c, v]) => [c, v[metric].score])),
      scale: SCORE_SCALE,
      level: 'county',
    })
  }, [active, d, metric, crop, lang, t, setCustomLayer])

  return (
    <div className="view">
      <div className="toolbar">
        <span className="muted small">{t('ingredient')}</span>
        <div className="chips">
          {B_CROPS.map((c) => <button key={c} type="button" className={`chip ${c === crop ? 'on' : ''}`} onClick={() => setCrop(c)}>{cropName(c, lang)}</button>)}
        </div>
      </div>
      {res.error && <p className="note warn">{t('error')}: {res.error}</p>}
      {!d && !res.error && <p className="muted pad">{t('loading')}</p>}
      {d?.proxy && <p className="note warn">{t('proxyNote')}</p>}
      {d && section === 'sourcing' && <Sourcing d={d} metric={metric} setMetric={setMetric} selected={selectedCounty} />}
      {d && section === 'recs' && <Recs d={d} />}
      {d && section === 'trends' && <Trends d={d} />}
    </div>
  )
}

function Sourcing({ d, metric, setMetric, selected }: { d: ProcurementResponse; metric: Metric; setMetric: (m: Metric) => void; selected: string | null }) {
  const { t } = useI18n()
  const x = useExplain()
  const P = x.procurement
  const { setHighlight, hoveredOnMap, selectArea } = useMapLink()
  const rows = Object.entries(d.counties).sort((a, b) => (b[1].availability.production_t_median_5y ?? 0) - (a[1].availability.production_t_median_5y ?? 0))
  const total = rows.reduce((s, [, v]) => s + (v.availability.production_t_median_5y ?? 0), 0)
  const hovered = hoveredOnMap?.split('-')[0]
  useEffect(() => () => setHighlight(null), [setHighlight])

  return (
    <div className="stack">
      <div className="toolbar">
        <span className="muted small">{t('mapMetric')}</span>
        <div className="seg">
          {METRICS.map((m) => <button key={m} type="button" className={m === metric ? 'on' : ''} onClick={() => setMetric(m)}>{t(m)}</button>)}
        </div>
        <Info>{x.general.scoreScale}</Info>
      </div>
      <div className="table-scroll">
        <table className="proc">
          <thead>
            <tr>
              <th>{t('county')}<div className="muted tiny">{t('confidence')} <Info>{P.confidence}</Info></div></th>
              <th className="num">{t('production5y')} <Info>{P.production5y}</Info><div className="muted tiny">{t('share')} <Info>{P.share}</Info></div></th>
              <th className={metric === 'availability' ? 'col-on' : ''}>{t('availability')} <Info wide><>{P.availability}<br /><br />{P.availabilitySub}</></Info></th>
              <th className={metric === 'quality' ? 'col-on' : ''}>{t('quality')} <Info>{P.quality}</Info><div className="muted tiny">{t('thisSeason')} <Info>{P.thisSeason}</Info></div></th>
              <th className={metric === 'impact' ? 'col-on' : ''}>
                {t('impact')} <Info>{P.impact}</Info>
                <div className="muted tiny">{t('waterNeed')} <Info wide>{P.water}</Info> · {t('emissions')} <Info wide>{P.emissions}</Info></div>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([code, v]) => (
              <tr
                key={code}
                className={`${code === selected ? 'sel' : ''} ${code === hovered ? 'hov' : ''}`}
                onMouseEnter={() => setHighlight(code)}
                onMouseLeave={() => setHighlight(null)}
                onClick={() => selectArea(code)}
              >
                <td><b>{v.name}</b><div><ConfidenceBadge level={v.confidence} info={false} short /></div></td>
                <td className="num">
                  {fmt(v.availability.production_t_median_5y)} t
                  <div className="muted tiny">{total ? fmt((100 * (v.availability.production_t_median_5y ?? 0)) / total) : '–'}%</div>
                </td>
                <td><Score s={v.availability.score} sub={`${v.availability.hazard_years}/${v.availability.years} bad yrs · CV ${fmt((v.availability.yield_cv ?? 0) * 100)}%`} /></td>
                <td>
                  <Score s={v.quality.score} sub={v.quality.latest_hits.length ? [...new Set(v.quality.latest_hits.map((h) => HAZARD_SHORT[h] ?? h))].join(', ') : undefined} />
                </td>
                <td>
                  <Score s={v.impact.score} />
                  <div className="muted tiny nowrap">{fmt(v.impact.dry_year_rain_mm)} / {v.impact.water_need_mm[0]}–{v.impact.water_need_mm[1]} mm</div>
                  <div className="muted tiny nowrap">{v.impact.emissions_kg_co2e_t === null ? '–' : `${fmt(v.impact.emissions_kg_co2e_t)} kg CO₂e/t`}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">{t('hintCounty')}</p>
    </div>
  )
}

function Recs({ d }: { d: ProcurementResponse }) {
  const { t } = useI18n()
  const P = useExplain().procurement
  return (
    <div className="recs">
      {d.recommendations.map((r, i) => (
        <div key={i} className={`rec rec-${r.type}`}>
          <h4>{r.title} {P[`rec_${r.type}` as keyof typeof P] && <Info wide>{P[`rec_${r.type}` as keyof typeof P]}</Info>}</h4>
          <p>{r.text}</p>
          {r.assumptions && <details><summary>{t('assumptions')}</summary><ul className="small">{r.assumptions.map((a) => <li key={a}>{a}</li>)}</ul></details>}
        </div>
      ))}
    </div>
  )
}

function Trends({ d }: { d: ProcurementResponse }) {
  const { t } = useI18n()
  const P = useExplain().procurement
  const rows = useMemo(
    () => Object.entries(d.counties).sort((a, b) => (b[1].availability.production_t_median_5y ?? 0) - (a[1].availability.production_t_median_5y ?? 0)),
    [d],
  )
  const chart = useMemo<ChartOption>(() => {
    const years = rows[0]?.[1].availability.series.years ?? []
    return {
      grid: { left: 60, right: 12, top: 40, bottom: 26 },
      legend: { type: 'scroll', top: 0, textStyle: { fontSize: 11 }, itemHeight: 8, itemWidth: 12 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v)} t` },
      xAxis: { type: 'category', data: years.map(String), axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: rows.map(([, v], i) => ({
        name: v.name, type: 'bar', stack: 'p', barWidth: '60%',
        data: v.availability.series.production_t.map((n) => n ?? null), itemStyle: { color: PALETTE[i % PALETTE.length] },
      })),
    }
  }, [rows])
  return (
    <div className="stack">
      <Collapsible id="proc-production" title={t('productionChart')} info={P.productionChart} defaultOpen>
        <Chart option={chart} height={260} />
      </Collapsible>
      <Collapsible id="proc-data" title={t('dataUsed')}>
        <div className="block">
          <p><b>{t('source')}:</b></p>
          <ul className="small">{d.sources.map((s) => <li key={s}>{s}</li>)}</ul>
          <p><b>{t('assumptions')}:</b></p>
          <ul className="small">{d.assumptions.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
      </Collapsible>
    </div>
  )
}

function Score({ s, sub }: { s: number | null; sub?: string }) {
  return (
    <div className="score-cell">
      <div className="bar"><i style={{ width: `${s ?? 0}%`, background: scoreColor(s) }} /></div>
      <b style={{ color: scoreColor(s) }}>{s ?? '–'}</b>
      {sub && <div className="muted tiny">{sub}</div>}
    </div>
  )
}
