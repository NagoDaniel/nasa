import { useEffect, useMemo, useState } from 'react'
import { getProcurement } from '../../api/client'
import type { ProcurementResponse } from '../../api/types'
import Card from '../../components/Card'
import Chart, { PALETTE, type ChartOption } from '../../components/Chart'
import { fmt, scoreColor } from '../../components/format'
import Info from '../../components/Info'
import SourceNote, { ConfidenceBadge } from '../../components/SourceNote'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { B_CROPS, cropName } from '../../i18n/names'

export type Metric = 'availability' | 'quality' | 'impact'

const HAZARD_SHORT: Record<string, string> = {
  heat35_jul_aug: 'heat ≥35 °C', heat32_jul_aug: 'hot summer', heat30_jun: 'June heat', rootmoist_jja_z: 'dry soil',
  dry_spell_apr_sep: 'dry spell', rain_flowering_small_grain: 'wet flowering', wet_days_flowering_small_grain: 'wet flowering',
  late_frost: 'late frost', rain_harvest_small_grain: 'wet harvest', rain_harvest_summer_crops: 'wet harvest',
}

export default function ProcurementView({ onChoropleth, selectedCounty }: {
  onChoropleth: (v: { values: Record<string, number | null>; label: string } | null) => void
  selectedCounty: string | null
}) {
  const { t, lang } = useI18n()
  const [crop, setCrop] = useState('maize')
  const [metric, setMetric] = useState<Metric>('availability')
  const res = useAsync(crop, () => getProcurement(crop))
  const d = res.data

  useEffect(() => {
    if (!d) return
    const values = Object.fromEntries(Object.entries(d.counties).map(([c, v]) => [c, v[metric].score]))
    onChoropleth({ values, label: `${t(metric)} — ${cropName(crop, lang)}` })
  }, [d, metric, crop, lang, t, onChoropleth])
  useEffect(() => () => onChoropleth(null), [onChoropleth])

  return (
    <div className="view">
      <h2 className="section">{t('procTitle')}</h2>
      <p className="muted small section-sub">{t('procSub')}</p>
      <div className="toolbar">
        <span className="muted small">{t('ingredient')}:</span>
        <div className="seg wrap">
          {B_CROPS.map((c) => <button key={c} className={c === crop ? 'on' : ''} onClick={() => setCrop(c)}>{cropName(c, lang)}</button>)}
        </div>
      </div>
      <div className="toolbar">
        <span className="muted small">{t('mapMetric')}:</span>
        <div className="seg">
          {(['availability', 'quality', 'impact'] as Metric[]).map((m) => <button key={m} className={m === metric ? 'on' : ''} onClick={() => setMetric(m)}>{t(m)}</button>)}
        </div>
      </div>
      {res.error && <p className="note warn">{t('error')}: {res.error}</p>}
      {!d && !res.error && <p className="muted pad">{t('loading')}</p>}
      {d && <Body d={d} crop={crop} selected={selectedCounty} />}
    </div>
  )
}

function Body({ d, crop, selected }: { d: ProcurementResponse; crop: string; selected: string | null }) {
  const { t, lang } = useI18n()
  const x = useExplain()
  const P = x.procurement
  const rows = Object.entries(d.counties).sort((a, b) => (b[1].availability.production_t_median_5y ?? 0) - (a[1].availability.production_t_median_5y ?? 0))
  const total = rows.reduce((s, [, v]) => s + (v.availability.production_t_median_5y ?? 0), 0)

  const chart = useMemo<ChartOption>(() => {
    const years = rows[0]?.[1].availability.series.years ?? []
    return {
      grid: { left: 56, right: 12, top: 34, bottom: 24 },
      legend: { top: 0, textStyle: { fontSize: 10 }, itemHeight: 8, itemWidth: 12 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v)} t` },
      xAxis: { type: 'category', data: years.map(String), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: rows.map(([, v], i) => ({
        name: v.name, type: 'bar', stack: 'p', barWidth: '60%',
        data: v.availability.series.production_t.map((x) => x ?? null), itemStyle: { color: PALETTE[i % PALETTE.length] },
      })),
    }
  }, [rows])

  return (
    <>
      {d.proxy && <p className="note warn">{t('proxyNote')}</p>}
      <Card title={`${cropName(crop, lang)} — ${t('availability')} · ${t('quality')} · ${t('impact')}`} info={x.general.scoreScale}>
        <div className="table-scroll">
          <table className="proc">
            <thead>
              <tr>
                <th>{t('county')}</th>
                <th className="num">{t('production5y')} <Info>{P.production5y}</Info><div className="muted tiny">{t('share')} <Info>{P.share}</Info></div></th>
                <th>{t('availability')} <Info wide><>{P.availability}<br /><br />{P.availabilitySub}</></Info></th>
                <th>{t('quality')} <Info>{P.quality}</Info></th>
                <th>{t('thisSeason')} <Info>{P.thisSeason}</Info></th>
                <th>
                  {t('impact')} <Info>{P.impact}</Info>
                  <div className="muted tiny">{t('waterNeed')} <Info wide>{P.water}</Info> · {t('emissions')} <Info wide>{P.emissions}</Info></div>
                </th>
                <th>{t('confidence')} <Info>{P.confidence}</Info></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([code, v]) => (
                <tr key={code} className={code === selected ? 'sel' : ''}>
                  <td><b>{v.name}</b></td>
                  <td className="num">
                    {fmt(v.availability.production_t_median_5y)} t
                    <div className="muted tiny">{total ? fmt((100 * (v.availability.production_t_median_5y ?? 0)) / total) : '–'}%</div>
                  </td>
                  <td><Score s={v.availability.score} sub={`${v.availability.hazard_years}/${v.availability.years} bad yrs · CV ${fmt((v.availability.yield_cv ?? 0) * 100)}%`} /></td>
                  <td><Score s={v.quality.score} /></td>
                  <td className="small">{v.quality.latest_hits.length ? [...new Set(v.quality.latest_hits.map((h) => HAZARD_SHORT[h] ?? h))].join(', ') : <span className="muted">–</span>}</td>
                  <td>
                    <Score s={v.impact.score} />
                    <div className="muted tiny nowrap">{fmt(v.impact.dry_year_rain_mm)} / {v.impact.water_need_mm[0]}–{v.impact.water_need_mm[1]} mm</div>
                    <div className="muted tiny nowrap">{v.impact.emissions_kg_co2e_t === null ? '–' : `${fmt(v.impact.emissions_kg_co2e_t)} kg CO₂e/t`}</div>
                  </td>
                  <td><ConfidenceBadge level={v.confidence} info={false} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={t('recommendations')}>
        <div className="recs">
          {d.recommendations.map((r, i) => (
            <div key={i} className={`rec rec-${r.type}`}>
              <h4>{r.title} {P[`rec_${r.type}` as keyof typeof P] && <Info wide>{P[`rec_${r.type}` as keyof typeof P]}</Info>}</h4>
              <p>{r.text}</p>
              {r.assumptions && <details><summary>{t('assumptions')}</summary><ul className="small">{r.assumptions.map((a) => <li key={a}>{a}</li>)}</ul></details>}
            </div>
          ))}
        </div>
      </Card>

      <Card title={t('productionChart')} info={P.productionChart}>
        <Chart option={chart} height={240} />
      </Card>

      <Card title={t('dataUsed')}>
        <SourceNote source={d.sources.join(' · ')} assumptions={d.assumptions} />
      </Card>
    </>
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
