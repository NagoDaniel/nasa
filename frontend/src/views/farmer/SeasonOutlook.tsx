import { useMemo, useState } from 'react'
import { getForecast } from '../../api/client'
import type { CountyForecast, Forecast } from '../../api/types'
import Chart, { type ChartOption } from '../../components/Chart'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import { CROPS, cropName } from '../../i18n/names'
import { OUTLOOK_TEXT, fill, type OutlookText } from './outlookText'

const tha = (kg: number) => fmt(kg / 1000, 1)

function verdict(T: OutlookText, pct: number): { word: string; tone: string } {
  if (pct <= -15) return { word: T.clearlyBelow, tone: 'bad' }
  if (pct <= -5) return { word: T.bitBelow, tone: 'warn' }
  if (pct < 5) return { word: T.close, tone: 'neutral' }
  if (pct < 15) return { word: T.bitAbove, tone: 'good' }
  return { word: T.clearlyAbove, tone: 'good' }
}

/** Horizontal range bar: 90 / 80 / 50 % intervals, best estimate and the normal year. */
function RangeBar({ T, iv, best, normal }: { T: OutlookText; iv: Record<string, [number, number]>; best: number; normal: number }) {
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
      <div title={T.bestEstimate} style={{ position: 'absolute', left: pos(best), top: 4, width: 3, height: 26, marginLeft: -1.5, background: 'var(--fg, #111)' }} />
      <div title={T.normalYear} style={{ position: 'absolute', left: pos(normal), top: 2, height: 30, borderLeft: '2px dashed #6b7280' }} />
      <div className="muted small" style={{ position: 'absolute', left: pos(normal), top: 34, transform: 'translateX(-50%)', whiteSpace: 'nowrap' }}>{T.normal} {tha(normal)}</div>
      <div className="small" style={{ position: 'absolute', left: pos(iv['90'][0]), top: 34, transform: 'translateX(-50%)' }}>{tha(iv['90'][0])}</div>
      <div className="small" style={{ position: 'absolute', left: pos(iv['90'][1]), top: 34, transform: 'translateX(-50%)' }}>{tha(iv['90'][1])}</div>
    </div>
  )
}

function TrackRecord({ T, c, f }: { T: OutlookText; c: CountyForecast; f: Forecast }) {
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
      legend: { top: 0, textStyle: { fontSize: 10 }, itemHeight: 8, data: [T.range80, T.model, T.actual] },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => (v == null ? '–' : `${fmt(v, 1)} t/ha`) },
      xAxis: { type: 'category', data: years, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: 't/ha', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: [
        { name: 'band-low', type: 'line', data: low.map(t), stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: T.range80, type: 'line', data: high.map((v, i) => (v == null || low[i] == null ? null : (v - (low[i] as number)) / 1000)), stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, itemStyle: { color: 'rgba(22,163,74,.35)' }, areaStyle: { color: 'rgba(22,163,74,.18)' }, tooltip: { show: false } },
        { name: T.model, type: 'line', data: years.map((y) => (fc && y === String(fc.year) ? fc.yield_kg_ha / 1000 : t(at(y)?.predicted_kg_ha))), symbolSize: 4, lineStyle: { color: '#16a34a', width: 2 }, itemStyle: { color: '#16a34a' } },
        { name: T.actual, type: 'line', data: years.map((y) => t(at(y)?.actual_kg_ha)), symbolSize: 6, lineStyle: { opacity: 0 }, itemStyle: { color: '#374151' } },
      ],
    } as ChartOption
  }, [c, T])
  return (
    <>
      <Chart option={option} height={220} />
      <p className="muted small">
        {T.trackA}<i>{T.trackItalic}</i>{T.trackB}
        {f.coverage_80_pct != null && fill(T.trackCov, { p: f.coverage_80_pct })}{T.trackLast}
      </p>
    </>
  )
}

/** Season yield outlook for the county of the selected area (ridge model, tested leave-one-year-out). */
export default function SeasonOutlook({ county, countyName }: { county: string; countyName: string }) {
  const { lang } = useI18n()
  const T = OUTLOOK_TEXT[lang]
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
          {!m && <p className="note warn">{fill(T.notEnough, { name: name.toLowerCase() })}</p>}

          {m && !fc && <p className="note">{fill(T.noWeather, { county: countyName })}</p>}

          {fc && m && (() => {
            const v = verdict(T, fc.anomaly_pct)
            const iv = fc.intervals_kg_ha
            const drivers = [...fc.contributions].filter((x) => Math.abs(x.effect_pct) >= 1).sort((a, b) => Math.abs(b.effect_pct) - Math.abs(a.effect_pct))
            return (
              <>
                <p className="lead">
                  {fill(T.leadA, { name: name.toLowerCase(), county: countyName, year: fc.year })}<b>{fill(T.leadBold, { v: tha(fc.yield_kg_ha) })}</b>
                  {m.signal !== 'none'
                    ? <> — <span className={`tone-${v.tone}`}>{v.word}</span>{fill(T.leadSignal, { pct: `${fc.anomaly_pct >= 0 ? '+' : ''}${fmt(fc.anomaly_pct, 0)}`, year: fc.year, n: tha(fc.median_kg_ha) })}</>
                    : fill(T.leadNone, { year: fc.year, n: tha(fc.median_kg_ha) })}
                </p>
                <p className={`note ${m.signal === 'strong' ? '' : 'warn'}`}>
                  {m.signal === 'strong' && <><b>{T.strongB}</b>{fill(T.strongT, { p: m.skill_pct })}</>}
                  {m.signal === 'weak' && <><b>{T.weakB}</b>{fill(T.weakT, { p: m.skill_pct })}</>}
                  {m.signal === 'none' && <><b>{T.noneB}</b>{fill(T.noneT, { name: name.toLowerCase(), p: m.skill_pct })}</>}
                </p>
                <RangeBar T={T} iv={iv} best={fc.yield_kg_ha} normal={fc.median_kg_ha} />
                <ul className="small" style={{ margin: '0 0 4px', paddingLeft: 18 }}>
                  <li><b>{T.c50}</b> ({fill(T.interval, { p: 50 })}): {tha(iv['50'][0])}–{tha(iv['50'][1])} t/ha</li>
                  <li><b>{T.c80}</b> ({fill(T.interval, { p: 80 })}): {tha(iv['80'][0])}–{tha(iv['80'][1])} t/ha</li>
                  <li><b>{T.c90}</b> ({fill(T.interval, { p: 90 })}): {tha(iv['90'][0])}–{tha(iv['90'][1])} t/ha</li>
                </ul>
                <p className="hint">{T.chanceHint}</p>

                {m.signal !== 'none' && drivers.length > 0 && (
                  <>
                    <p className="small" style={{ marginBottom: 2 }}><b>{T.why}</b></p>
                    <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
                      {drivers.map((x) => (
                        <li key={x.key}>
                          <span className={x.effect_pct < 0 ? 'neg' : 'pos'} style={{ fontWeight: 600, color: x.effect_pct < 0 ? '#b91c1c' : '#15803d' }}>
                            {x.effect_pct >= 0 ? '+' : ''}{fmt(x.effect_pct, 0)} %
                          </span>{' '}
                          {x.label}{x.key !== 'trend' && <span className="muted"> ({T.thisSeason}: {fmt(x.value, 1)} {x.unit})</span>}
                        </li>
                      ))}
                    </ul>
                    <p className="hint">{T.driversHint}</p>
                  </>
                )}

                {fc.supply && (
                  <p className="small">
                    <b>{T.buyersB}</b>{fill(T.buyersA, { county: countyName, year: fc.supply.area_year, ha: fmt(fc.supply.area_ha, 0) })}<b>{fmt(fc.supply.production_t, 0)} t</b>
                    {fill(T.buyersC, { lo: fmt(fc.supply.low_t, 0), hi: fmt(fc.supply.high_t, 0), n: fmt(fc.supply.normal_t, 0) })}
                    {fc.supply.latest_t ? fill(T.buyersLatest, { t: fmt(fc.supply.latest_t, 0), y: fc.supply.latest_year ?? '' }) : ''}.
                  </p>
                )}
              </>
            )
          })()}

          {c && c.history.length > 0 && m && <TrackRecord T={T} c={c} f={f} />}

          {m && (
            <details className="small">
              <summary>{T.howTitle}</summary>
              <p>
                {fill(T.howText, { n: m.n_county_years, a: m.years[0], b: m.years[1], name: name.toLowerCase(), mae: fmt(m.mae_pct, 0),
                  base: fmt(m.mae_normal_year_pct, 0), skill: m.skill_pct })}
              </p>
              <p>{fill(T.learned, { list: m.predictors.map((p) => `${p.label}: ${p.effect_pct_per_unit >= 0 ? '+' : ''}${fmt(p.effect_pct_per_unit, 2)} % ${T.per} ${p.unit}`).join('; ') })}</p>
            </details>
          )}

          <SourceNote
            source={f.sources.join('; ')}
            period={m ? `${m.years[0]}–${m.years[1]}${fc ? ` → ${fc.year}` : ''}` : undefined}
            resolution={T.resolution}
            confidence={m?.signal === 'strong' && !f.proxy ? 'medium' : 'low'}
            note={`${T.aiRole}${f.proxy ? fill(T.proxy, { p: cropName(f.proxy, lang) }) : ''}${T.fails}${f.limits.join(' ')}`}
            assumptions={f.method}
          />
        </>
      )}
    </div>
  )
}
