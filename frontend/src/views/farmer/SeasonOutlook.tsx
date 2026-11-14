import { useMemo, useState } from 'react'
import { getForecast } from '../../api/client'
import type { CountyForecast, Forecast } from '../../api/types'
import Chart, { type ChartOption } from '../../components/Chart'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import { CROPS, cropName } from '../../i18n/names'

const tha = (kg: number) => fmt(kg / 1000, 1)

function verdict(pct: number): { word: string; tone: string } {
  if (pct <= -15) return { word: 'clearly below a normal year', tone: 'bad' }
  if (pct <= -5) return { word: 'a bit below a normal year', tone: 'warn' }
  if (pct < 5) return { word: 'close to a normal year', tone: 'neutral' }
  if (pct < 15) return { word: 'a bit above a normal year', tone: 'good' }
  return { word: 'clearly above a normal year', tone: 'good' }
}

/** Horizontal range bar: 90 / 80 / 50 % intervals, best estimate and the normal year. */
function RangeBar({ iv, best, normal }: { iv: Record<string, [number, number]>; best: number; normal: number }) {
  const lo = Math.min(iv['90'][0], normal) * 0.95
  const hi = Math.max(iv['90'][1], normal) * 1.05
  const pos = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`
  const seg = (k: string, op: number) => (
    <div style={{ position: 'absolute', left: pos(iv[k][0]), width: `calc(${pos(iv[k][1])} - ${pos(iv[k][0])})`, top: 8, height: 18, background: 'var(--accent)', opacity: op, borderRadius: 4 }} />
  )
  return (
    <div style={{ position: 'relative', height: 58, margin: '6px 4px 0' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 16, height: 2, background: 'var(--line, #e5e7eb)' }} />
      {seg('90', 0.18)}
      {seg('80', 0.3)}
      {seg('50', 0.55)}
      <div title="best estimate" style={{ position: 'absolute', left: pos(best), top: 4, width: 3, height: 26, marginLeft: -1.5, background: 'var(--fg, #111)' }} />
      <div title="normal year" style={{ position: 'absolute', left: pos(normal), top: 2, height: 30, borderLeft: '2px dashed #6b7280' }} />
      <div className="muted small" style={{ position: 'absolute', left: pos(normal), top: 34, transform: 'translateX(-50%)', whiteSpace: 'nowrap' }}>normal {tha(normal)}</div>
      <div className="small" style={{ position: 'absolute', left: pos(iv['90'][0]), top: 34, transform: 'translateX(-50%)' }}>{tha(iv['90'][0])}</div>
      <div className="small" style={{ position: 'absolute', left: pos(iv['90'][1]), top: 34, transform: 'translateX(-50%)' }}>{tha(iv['90'][1])}</div>
    </div>
  )
}

function TrackRecord({ c, f }: { c: CountyForecast; f: Forecast }) {
  const option = useMemo<ChartOption>(() => {
    const h = c.history
    const fc = c.forecast
    const years = [...h.map((r) => String(r.year)), ...(fc && !h.some((r) => r.year === fc.year) ? [String(fc.year)] : [])]
    const at = (y: string) => h.find((r) => String(r.year) === y)
    const low = years.map((y) => (fc && y === String(fc.year) ? fc.intervals_kg_ha['80'][0] : at(y)?.low_kg_ha ?? null))
    const high = years.map((y) => (fc && y === String(fc.year) ? fc.intervals_kg_ha['80'][1] : at(y)?.high_kg_ha ?? null))
    const t = (v: number | null | undefined) => (v == null ? null : v / 1000)
    return {
      grid: { left: 40, right: 12, top: 28, bottom: 24 },
      legend: { top: 0, textStyle: { fontSize: 10 }, itemHeight: 8, data: ['80 % range', 'Model (year hidden)', 'Actual (INS)'] },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => (v == null ? '–' : `${fmt(v, 1)} t/ha`) },
      xAxis: { type: 'category', data: years, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: 't/ha', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: [
        { name: 'band-low', type: 'line', data: low.map(t), stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: '80 % range', type: 'line', data: high.map((v, i) => (v == null || low[i] == null ? null : (v - (low[i] as number)) / 1000)), stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, itemStyle: { color: 'rgba(22,163,74,.35)' }, areaStyle: { color: 'rgba(22,163,74,.18)' }, tooltip: { show: false } },
        { name: 'Model (year hidden)', type: 'line', data: years.map((y) => (fc && y === String(fc.year) ? fc.yield_kg_ha / 1000 : t(at(y)?.predicted_kg_ha))), symbolSize: 4, lineStyle: { color: '#16a34a', width: 2 }, itemStyle: { color: '#16a34a' } },
        { name: 'Actual (INS)', type: 'line', data: years.map((y) => t(at(y)?.actual_kg_ha)), symbolSize: 6, lineStyle: { opacity: 0 }, itemStyle: { color: '#374151' } },
      ],
    } as ChartOption
  }, [c])
  return (
    <>
      <Chart option={option} height={220} />
      <p className="muted small">
        Grey dots: the real county yield. Green line: what the model would have said for each year <i>without having seen that year</i>; the green band is its 80 % range.
        {f.coverage_80_pct != null && <> The real yield fell inside the band in {f.coverage_80_pct} % of past years.</>} The last point is this season’s forecast.
      </p>
    </>
  )
}

/** Season yield outlook for the county of the selected area (ridge model, tested leave-one-year-out). */
export default function SeasonOutlook({ county, countyName }: { county: string; countyName: string }) {
  const { lang } = useI18n()
  const [crop, setCrop] = useState('maize')
  const res = useAsync(crop, () => getForecast(crop))
  const f = res.data
  const c = f?.counties[county]
  const fc = c?.forecast
  const m = fc?.model ?? f?.model
  const name = cropName(crop, lang)

  return (
    <div className="stack">
      <div className="chips">
        {CROPS.map((k) => (
          <button key={k} type="button" className={`chip ${k === crop ? 'on' : ''}`} onClick={() => setCrop(k)}>{cropName(k, lang)}</button>
        ))}
      </div>
      {res.error && <p className="note warn">{res.error}</p>}
      {!f && !res.error && <p className="muted">…</p>}
      {f && (
        <>
          {!m && <p className="note warn">Not enough county statistics to build a forecast for {name}.</p>}

          {m && !fc && <p className="note">No weather data for {countyName} this season yet, so no forecast. The chart shows how the model did in past years.</p>}

          {fc && m && (() => {
            const v = verdict(fc.anomaly_pct)
            const iv = fc.intervals_kg_ha
            const drivers = [...fc.contributions].filter((x) => Math.abs(x.effect_pct) >= 1).sort((a, b) => Math.abs(b.effect_pct) - Math.abs(a.effect_pct))
            return (
              <>
                <p className="lead">
                  Expected {name.toLowerCase()} yield in {countyName}, {fc.year}: <b>about {tha(fc.yield_kg_ha)} t/ha</b>
                  {m.signal !== 'none'
                    ? <> — <span className={`tone-${v.tone}`}>{v.word}</span> ({fc.anomaly_pct >= 0 ? '+' : ''}{fmt(fc.anomaly_pct, 0)} %; a normal {fc.year} would give {tha(fc.median_kg_ha)} t/ha).</>
                    : <> — about a normal year for {fc.year} ({tha(fc.median_kg_ha)} t/ha).</>}
                </p>
                <p className={`note ${m.signal === 'strong' ? '' : 'warn'}`}>
                  {m.signal === 'strong' && <><b>Weather signal: useful.</b> Knowing this season’s weather made past forecasts {m.skill_pct} % more accurate than the long-term trend alone.</>}
                  {m.signal === 'weak' && <><b>Weather signal: weak.</b> This season’s weather improved past forecasts by only {m.skill_pct} %; treat the direction as a hint.</>}
                  {m.signal === 'none' && <><b>Weather signal: none.</b> For {name.toLowerCase()}, the weather indicators we have did not improve past forecasts ({m.skill_pct} %). The range below is just the usual ups and downs around the long-term trend — still useful for planning, but it says nothing specific about this season.</>}
                </p>
                <RangeBar iv={iv} best={fc.yield_kg_ha} normal={fc.median_kg_ha} />
                <ul className="small" style={{ margin: '0 0 4px', paddingLeft: 18 }}>
                  <li><b>1 in 2 chance</b> (50 % interval): {tha(iv['50'][0])}–{tha(iv['50'][1])} t/ha</li>
                  <li><b>8 in 10 chance</b> (80 % interval): {tha(iv['80'][0])}–{tha(iv['80'][1])} t/ha</li>
                  <li><b>9 in 10 chance</b> (90 % interval): {tha(iv['90'][0])}–{tha(iv['90'][1])} t/ha</li>
                </ul>
                <p className="hint">“Chance” = how often the model’s range held in past years it had not seen.</p>

                {m.signal !== 'none' && drivers.length > 0 && (
                  <>
                    <p className="small" style={{ marginBottom: 2 }}><b>Why:</b></p>
                    <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
                      {drivers.map((x) => (
                        <li key={x.key}>
                          <span className={x.effect_pct < 0 ? 'neg' : 'pos'} style={{ fontWeight: 600, color: x.effect_pct < 0 ? '#b91c1c' : '#15803d' }}>
                            {x.effect_pct >= 0 ? '+' : ''}{fmt(x.effect_pct, 0)} %
                          </span>{' '}
                          {x.label}{x.key !== 'trend' && <span className="muted"> (this season: {fmt(x.value, 1)} {x.unit})</span>}
                        </li>
                      ))}
                    </ul>
                    <p className="hint">Each line: how much that factor moved the expected yield compared with an average season.</p>
                  </>
                )}

                {fc.supply && (
                  <p className="small">
                    <b>For buyers:</b> {countyName} at the {fc.supply.area_year} area ({fmt(fc.supply.area_ha, 0)} ha) that is about <b>{fmt(fc.supply.production_t, 0)} t</b>{' '}
                    (8 in 10: {fmt(fc.supply.low_t, 0)}–{fmt(fc.supply.high_t, 0)} t), vs {fmt(fc.supply.normal_t, 0)} t in a normal year
                    {fc.supply.latest_t ? ` and ${fmt(fc.supply.latest_t, 0)} t in ${fc.supply.latest_year}` : ''}.
                  </p>
                )}
              </>
            )
          })()}

          {c && c.history.length > 0 && m && <TrackRecord c={c} f={f} />}

          {m && (
            <details className="small">
              <summary>How the forecast works</summary>
              <p>
                A simple statistical model (ridge regression) learned from {m.n_county_years} county-years ({m.years[0]}–{m.years[1]}, 8 counties) how {name.toLowerCase()} yields
                moved with the long-term trend and with the weather in the crop’s sensitive period. Tested on each past year without seeing it: average miss {fmt(m.mae_pct, 0)} %,
                versus {fmt(m.mae_normal_year_pct, 0)} % for the trend alone ({m.skill_pct} % better).
              </p>
              <p>Learned effects: {m.predictors.map((p) => `${p.label}: ${p.effect_pct_per_unit >= 0 ? '+' : ''}${fmt(p.effect_pct_per_unit, 2)} % per ${p.unit}`).join('; ')}.</p>
            </details>
          )}

          <SourceNote
            source={f.sources.join('; ')}
            period={m ? `${m.years[0]}–${m.years[1]}${fc ? ` → ${fc.year}` : ''}` : undefined}
            resolution="county (INS statistics) · weather ~50 km"
            confidence={m?.signal === 'strong' && !f.proxy ? 'medium' : 'low'}
            note={`AI role: forecasting. ${f.proxy ? `Uses '${f.proxy}' statistics as proxy. ` : ''}Where it fails: ${f.limits.join(' ')}`}
            assumptions={f.method}
          />
        </>
      )}
    </div>
  )
}
