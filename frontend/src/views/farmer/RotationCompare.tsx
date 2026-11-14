import { useEffect, useMemo, useState } from 'react'
import { scoreRotations } from '../../api/client'
import type { Priorities, RotationResult } from '../../api/types'
import Card from '../../components/Card'
import Chart, { PALETTE, type ChartOption } from '../../components/Chart'
import { fmt, scoreColor } from '../../components/format'
import { ConfidenceBadge } from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { CROPS, cropName } from '../../i18n/names'

type Rot = { name: string; crops: string[] }

const PRESETS: Rot[] = [
  { name: 'Maize – wheat – maize', crops: ['maize', 'wheat', 'maize'] },
  { name: 'Pea – maize – oats – sunflower', crops: ['pea', 'maize', 'oats', 'sunflower'] },
  { name: 'Barley – pea – wheat – maize', crops: ['barley', 'pea', 'wheat', 'maize'] },
  { name: 'Oats – soy – wheat – sunflower', crops: ['oats', 'soy', 'wheat', 'sunflower'] },
]
const SUB: (keyof Priorities)[] = ['yield', 'water', 'soil', 'risk']

export default function RotationCompare({ unitId, priorities }: { unitId: string; priorities: Priorities }) {
  const { t, lang } = useI18n()
  const [rots, setRots] = useState<Rot[]>(PRESETS.slice(0, 2))
  const [results, setResults] = useState<RotationResult[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    const ctl = new AbortController()
    const id = setTimeout(() => {
      setBusy(true)
      scoreRotations(unitId, priorities, rots, ctl.signal)
        .then((r) => { setResults(r.results); setErr(null) })
        .catch((e) => { if (!ctl.signal.aborted) setErr(String(e.message ?? e)) })
        .finally(() => { if (!ctl.signal.aborted) setBusy(false) })
    }, 250)
    return () => { clearTimeout(id); ctl.abort() }
  }, [unitId, priorities, rots])

  const update = (i: number, r: Rot) => setRots(rots.map((x, j) => (j === i ? r : x)))
  const label = (r: Rot) => r.crops.map((c) => cropName(c, lang)).join(' – ')

  const bars = useMemo<ChartOption | null>(() => results && {
    grid: { left: 8, right: 36, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value', max: 100, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
    yAxis: { type: 'category', inverse: true, data: results.map((r, i) => `${i + 1}. ${label(r)}`), axisLabel: { fontSize: 11, width: 220, overflow: 'truncate' } },
    series: [{ type: 'bar', barWidth: 18, data: results.map((r, i) => ({ value: r.total, itemStyle: { color: PALETTE[i] } })),
      label: { show: true, position: 'right', fontWeight: 'bold' } }],
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, lang])

  const radar = useMemo<ChartOption | null>(() => results && {
    legend: { bottom: 0, textStyle: { fontSize: 10 }, itemHeight: 8 },
    tooltip: {},
    radar: { indicator: SUB.map((k) => ({ name: t(`p_${k}` as const), max: 100 })), radius: '62%', center: ['50%', '45%'], axisName: { fontSize: 11, color: '#374151' } },
    series: [{ type: 'radar', data: results.map((r, i) => ({ name: `${i + 1}`, value: SUB.map((k) => r.scores[k]), lineStyle: { color: PALETTE[i] }, itemStyle: { color: PALETTE[i] }, areaStyle: { color: PALETTE[i], opacity: 0.08 } })) }],
  }, [results, t])

  return (
    <Card title={t('rotations')} sub={t('rotationsSub')} right={busy ? <span className="muted small">{t('scoring')}</span> : undefined}>
      <div className="rot-editors">
        {rots.map((r, i) => (
          <div key={i} className="rot-editor" style={{ borderLeftColor: PALETTE[i] }}>
            <div className="rot-row">
              <b>{i + 1}.</b>
              {r.crops.map((c, y) => (
                <select key={y} value={c} aria-label={`${t('year')} ${y + 1}`}
                  onChange={(e) => update(i, { ...r, crops: r.crops.map((x, k) => (k === y ? e.target.value : x)) })}>
                  {CROPS.map((id) => <option key={id} value={id}>{cropName(id, lang)}</option>)}
                </select>
              ))}
              {r.crops.length < 4 && <button className="ghost" onClick={() => update(i, { ...r, crops: [...r.crops, 'pea'] })}>{t('addYear')}</button>}
              {r.crops.length > 3 && <button className="ghost" onClick={() => update(i, { ...r, crops: r.crops.slice(0, -1) })}>{t('removeYear')}</button>}
              {rots.length > 1 && <button className="ghost danger" onClick={() => setRots(rots.filter((_, j) => j !== i))}>{t('remove')}</button>}
            </div>
          </div>
        ))}
        <div className="rot-row">
          {rots.length < 3 && <button onClick={() => setRots([...rots, PRESETS[(rots.length) % PRESETS.length]])}>{t('addRotation')}</button>}
          <span className="muted small">{t('presets')}:</span>
          {PRESETS.map((p) => (
            <button key={p.name} className="ghost small" onClick={() => setRots(rots.length < 3 ? [...rots, p] : [...rots.slice(0, 2), p])}>
              {label(p)}
            </button>
          ))}
        </div>
      </div>

      {err && <p className="note warn">{err}</p>}
      {results && bars && radar && (
        <>
          <div className="rot-charts">
            <div><h4>{t('total')}</h4><Chart option={bars} height={40 + results.length * 34} /></div>
            <div><Chart option={radar} height={230} /></div>
          </div>
          <div className="rot-details">
            {results.map((r, i) => (
              <div key={i} className="rot-detail" style={{ borderTopColor: PALETTE[i] }}>
                <div className="rot-detail-head">
                  <b>{i + 1}. {label(r)}</b>
                  <ConfidenceBadge level={r.confidence.level} />
                </div>
                <div className="score-row">
                  {SUB.map((k) => (
                    <div key={k} className="score-chip" style={{ borderColor: scoreColor(r.scores[k]) }}>
                      <span className="muted small">{t(`p_${k}` as const)}</span>
                      <b style={{ color: scoreColor(r.scores[k]) }}>{r.scores[k]}</b>
                    </div>
                  ))}
                  <div className="score-chip total"><span className="muted small">{t('total')}</span><b>{r.total}</b></div>
                </div>
                <table className="years">
                  <tbody>
                    {r.years.map((y) => (
                      <tr key={y.year}>
                        <td>{t('year')} {y.year}</td>
                        <td><b>{cropName(y.crop, lang)}</b></td>
                        <td className="muted small">{t('expectedYield')}: {fmt(y.expected_yield_kg_ha[0])}–{fmt(y.expected_yield_kg_ha[1])} kg/ha</td>
                        <td className="small">{y.effects.join('; ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <details>
                  <summary>{t('why')}</summary>
                  {SUB.map((k) => (
                    <div key={k} className="factors">
                      <h5>{t(`p_${k}` as const)} — {r.scores[k]}</h5>
                      <ul>
                        {r.factors[k].map((f, j) => (
                          <li key={j} className={`eff eff-${f.effect === '+' ? 'pos' : f.effect === '−' ? 'neg' : 'neu'}`}>
                            <span className="eff-mark">{f.effect}</span>
                            <div>
                              <div>{f.label}: <b>{f.value}</b></div>
                              <div className="muted small">{f.source}{f.assumption ? ` — ${f.assumption}` : ''}</div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  <ul className="muted small">{r.confidence.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                </details>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}
