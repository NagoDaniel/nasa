import { useMemo, useState } from 'react'
import type { Indicator } from '../../api/types'
import Chart, { type ChartOption } from '../../components/Chart'
import { fmt } from '../../components/format'
import Info from '../../components/Info'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { indicatorLabel } from '../../i18n/names'
import { useMapLink } from '../../state/MapLink'
import { MONTHS, monthly, yearly } from './series'

const AXIS = { axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: '#eef0f3' } } }

/** One indicator: yearly bars (click a bar → that year on the map) or the seasonal curve. */
export default function IndicatorChart({ ind, color, kind }: { ind: Indicator; color: string; kind: 'county' | 'commune' }) {
  const { t, lang } = useI18n()
  const x = useExplain()
  const { year, setYear, years } = useMapLink()
  // a one-year sample has no meaningful per-year view
  const [mode, setMode] = useState<'annual' | 'seasonal'>(ind.status === 'sample' ? 'seasonal' : 'annual')
  const ys = useMemo(() => yearly(ind), [ind])
  const valid = ys.filter((y) => !y.partial && y.value !== null)
  const mean = valid.length ? valid.reduce((a, y) => a + (y.value as number), 0) / valid.length : null
  const yUnit = ind.aggregation === 'sum' ? `${ind.unit}/yr` : ind.unit
  const nd = Math.abs(mean ?? 0) < 10 ? 1 : 0
  const avgLabel = `${t('average')} ${ind.keys[0].slice(0, 4)}–${ind.keys[ind.keys.length - 1].slice(0, 4)}`

  const option = useMemo<ChartOption>(() => {
    if (mode === 'annual') {
      return {
        grid: { left: 48, right: 14, top: 24, bottom: 26 },
        tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v, nd)} ${yUnit}` },
        xAxis: { type: 'category', data: ys.map((y) => (y.partial ? `${y.year}*` : String(y.year))), axisLabel: { fontSize: 11 } },
        yAxis: { type: 'value', name: yUnit, nameTextStyle: { fontSize: 11, align: 'left' }, ...AXIS },
        series: [{
          type: 'bar',
          barMaxWidth: 34,
          data: ys.map((y) => {
            const on = String(y.year) === year
            return { value: y.value, itemStyle: { color, opacity: y.partial ? 0.35 : on ? 1 : 0.6, borderColor: on ? '#111827' : 'transparent', borderWidth: on ? 2 : 0, borderRadius: [3, 3, 0, 0] } }
          }),
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
      grid: { left: 48, right: 14, top: 30, bottom: 26 },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11 }, itemHeight: 8 },
      tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v, 1)} ${ind.unit}` },
      xAxis: { type: 'category', data: MONTHS, axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', name: ind.unit, nameTextStyle: { fontSize: 11, align: 'left' }, ...AXIS },
      series: [
        { name: avgLabel, type: 'line', data: m.avg, symbol: 'none', lineStyle: { color: '#9ca3af', width: 2 }, areaStyle: { color: 'rgba(156,163,175,.15)' } },
        { name: String(m.lastYear), type: 'line', data: m.latest, symbolSize: 5, lineStyle: { color, width: 2.5 }, itemStyle: { color } },
      ],
    }
  }, [mode, ys, ind, color, mean, nd, yUnit, avgLabel, year])

  const partial = ys.filter((y) => y.partial && y.n > 0).map((y) => `${y.year} (${y.n} ${ind.period.step === 'month' ? 'mo' : 'obs'})`)
  return (
    <div className="block">
      <div className="block-head">
        <div>
          <h3>
            {indicatorLabel(ind.name, ind.label, lang)} <Info>{x.indicators[ind.name] ?? ind.label}</Info>
            {ind.status === 'sample' && <> <span className="badge sample">{t('sample')}</span></>}
          </h3>
          <p className="muted small">{yUnit}</p>
        </div>
        <div className="nowrap">
          <div className="seg">
            <button type="button" className={mode === 'annual' ? 'on' : ''} onClick={() => setMode('annual')}>{t('annual')}</button>
            <button type="button" className={mode === 'seasonal' ? 'on' : ''} onClick={() => setMode('seasonal')}>{t('seasonal')}</button>
          </div>{' '}
          <Info>{mode === 'annual' ? x.general.perYear : x.general.byMonth}</Info>
        </div>
      </div>
      <Chart
        option={option}
        height={250}
        onAxisClick={mode === 'annual' ? (i) => {
          const y = ys[i] && String(ys[i].year)
          if (y && years?.includes(y)) setYear(y)
        } : undefined}
      />
      {mode === 'annual' && years && years.length > 1 && <p className="hint">{t('hintBar')}</p>}
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
    </div>
  )
}
