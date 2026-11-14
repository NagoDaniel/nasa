import { useMemo, useState } from 'react'
import type { Indicator } from '../../api/types'
import Card from '../../components/Card'
import Chart, { type ChartOption } from '../../components/Chart'
import { fmt } from '../../components/format'
import Info from '../../components/Info'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { indicatorLabel } from '../../i18n/names'

const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

export function yearly(ind: Indicator) {
  const by = new Map<number, number[]>()
  ind.keys.forEach((k, i) => {
    const v = ind.values[i]
    const y = Number(k.slice(0, 4))
    if (!by.has(y)) by.set(y, [])
    if (v !== null) by.get(y)!.push(v)
  })
  const years = [...by.keys()].sort()
  const steps = ind.period.step === 'month' ? 12 : 23
  return years.map((y) => {
    const vs = by.get(y)!
    const val = vs.length === 0 ? null : ind.aggregation === 'sum' ? vs.reduce((a, b) => a + b, 0) : vs.reduce((a, b) => a + b, 0) / vs.length
    return { year: y, value: val, partial: vs.length < steps, n: vs.length }
  })
}

function monthly(ind: Indicator) {
  const sums = Array(12).fill(0)
  const counts = Array(12).fill(0)
  ind.keys.forEach((k, i) => {
    const v = ind.values[i]
    if (v === null) return
    const m = Number(k.slice(5, 7)) - 1
    sums[m] += v
    counts[m] += 1
  })
  const avg = sums.map((s, i) => (counts[i] ? s / counts[i] : null))
  const lastYear = Number(ind.keys[ind.keys.length - 1].slice(0, 4))
  const latest = Array(12).fill(null) as (number | null)[]
  ind.keys.forEach((k, i) => {
    if (Number(k.slice(0, 4)) === lastYear) latest[Number(k.slice(5, 7)) - 1] = ind.values[i]
  })
  return { avg, latest, lastYear }
}

export default function IndicatorCard({ ind, color, kind }: { ind: Indicator; color: string; kind: 'county' | 'commune' }) {
  const { t, lang } = useI18n()
  const x = useExplain()
  // a one-year sample has no meaningful per-year view
  const [mode, setMode] = useState<'annual' | 'seasonal'>(ind.status === 'sample' ? 'seasonal' : 'annual')
  const ys = useMemo(() => yearly(ind), [ind])
  const valid = ys.filter((y) => !y.partial && y.value !== null)
  const mean = valid.length ? valid.reduce((a, y) => a + (y.value as number), 0) / valid.length : null
  const yUnit = ind.aggregation === 'sum' ? `${ind.unit}/yr` : ind.unit
  const avgLabel = `${t('average')} ${ind.keys[0].slice(0, 4)}–${ind.keys[ind.keys.length - 1].slice(0, 4)}`
  const nd = Math.abs(mean ?? 0) < 10 ? 1 : 0

  const option = useMemo<ChartOption>(() => {
    if (mode === 'annual') {
      return {
        grid: { left: 44, right: 12, top: 18, bottom: 24 },
        tooltip: {
          trigger: 'axis',
          valueFormatter: (v: number) => `${fmt(v, nd)} ${yUnit}`,
        },
        xAxis: { type: 'category', data: ys.map((y) => (y.partial ? `${y.year}*` : String(y.year))), axisLabel: { fontSize: 10 } },
        yAxis: { type: 'value', name: yUnit, nameTextStyle: { fontSize: 10, align: 'left' }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
        series: [{
          type: 'bar',
          data: ys.map((y) => ({ value: y.value, itemStyle: { color, opacity: y.partial ? 0.35 : 0.9 } })),
          markLine: mean === null ? undefined : {
            symbol: 'none', silent: true, lineStyle: { color: '#6b7280', type: 'dashed' },
            label: { formatter: `${avgLabel}: ${fmt(mean, nd)}`, fontSize: 10, position: 'insideEndTop' },
            data: [{ yAxis: mean }],
          },
        }],
      }
    }
    const m = monthly(ind)
    return {
      grid: { left: 44, right: 12, top: 26, bottom: 24 },
      legend: { top: 0, right: 0, textStyle: { fontSize: 10 }, itemHeight: 8 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v, 1)} ${ind.unit}` },
      xAxis: { type: 'category', data: MONTHS, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: ind.unit, nameTextStyle: { fontSize: 10, align: 'left' }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
      series: [
        { name: avgLabel, type: 'line', data: m.avg, symbol: 'none', lineStyle: { color: '#9ca3af', width: 2 }, areaStyle: { color: 'rgba(156,163,175,.15)' } },
        { name: String(m.lastYear), type: 'line', data: m.latest, symbolSize: 4, lineStyle: { color, width: 2 }, itemStyle: { color } },
      ],
    }
  }, [mode, ys, ind, color, mean, nd, yUnit, avgLabel])

  const partial = ys.filter((y) => y.partial && y.n > 0).map((y) => `${y.year} (${y.n} ${ind.period.step === 'month' ? 'mo' : 'obs'})`)
  return (
    <Card
      title={<>{indicatorLabel(ind.name, ind.label, lang)} {ind.status === 'sample' && <span className="badge sample">{t('sample')}</span>}</>}
      info={x.indicators[ind.name] ?? ind.label}
      sub={`${ind.variable} · ${ind.unit}`}
      right={
        <div className="nowrap">
          <div className="seg">
            <button className={mode === 'annual' ? 'on' : ''} onClick={() => setMode('annual')}>{t('annual')}</button>
            <button className={mode === 'seasonal' ? 'on' : ''} onClick={() => setMode('seasonal')}>{t('seasonal')}</button>
          </div>{' '}
          <Info>{mode === 'annual' ? x.general.perYear : x.general.byMonth}</Info>
        </div>
      }
    >
      <Chart option={option} height={190} />
      <SourceNote
        source={ind.source}
        period={`${ind.period.start} – ${ind.period.end}`}
        resolution={ind.resolution}
        confidence={ind.confidence[kind]}
        note={ind.confidence.note}
        extra={[
          partial.length ? `* ${t('partialYear')}: ${partial.join(', ')}` : '',
          ind.missing_periods?.length ? `${t('missing')}: ${ind.missing_periods.join(', ')}` : '',
        ].filter(Boolean).join(' · ') || undefined}
      />
    </Card>
  )
}
