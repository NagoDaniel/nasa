import { useMemo } from 'react'
import type { AreaBundle } from '../../api/types'
import Card from '../../components/Card'
import Chart, { PALETTE, type ChartOption } from '../../components/Chart'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { cropName } from '../../i18n/names'

const SHOW = ['maize', 'wheat', 'barley', 'oats', 'sunflower', 'pea', 'soy']

export default function CropStatsCard({ stats, countyName }: { stats: AreaBundle['crop_stats']; countyName: string }) {
  const { t, lang } = useI18n()
  const x = useExplain()
  const option = useMemo<ChartOption>(() => ({
    grid: { left: 48, right: 12, top: 30, bottom: 24 },
    legend: { type: 'scroll', top: 0, textStyle: { fontSize: 10 }, itemHeight: 8, itemWidth: 14 },
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${fmt(v)} kg/ha` },
    xAxis: { type: 'category', data: stats.years.map(String), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: 'kg/ha', nameTextStyle: { fontSize: 10, align: 'left' }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: '#eef0f3' } } },
    series: SHOW.filter((c) => stats.values[c]?.yield_kg_ha?.some((v) => v)).map((c, i) => ({
      name: cropName(c, lang), type: 'line', connectNulls: false, symbolSize: 4,
      data: stats.values[c].yield_kg_ha!.map((v) => (v ? v : null)),
      lineStyle: { width: 2, color: PALETTE[i] }, itemStyle: { color: PALETTE[i] },
    })),
  }), [stats, lang])
  return (
    <Card title={`${t('cropStats')}: ${countyName}`} sub={t('cropStatsSub')} info={x.cropStats}>
      <Chart option={option} height={220} />
      <SourceNote source={stats.source} period={`${stats.years[0]}–${stats.years[stats.years.length - 1]}`} confidence={stats.confidence.county} note={stats.confidence.note} />
    </Card>
  )
}
