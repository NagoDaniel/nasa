import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, RadarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  RadarComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, LineChart, RadarChart, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent,
  RadarComponent, TooltipComponent, CanvasRenderer])

export type ChartOption = echarts.EChartsCoreOption

export const PALETTE = ['#2563eb', '#d97706', '#059669', '#9333ea', '#dc2626', '#0891b2', '#65a30d', '#db2777', '#475569']

const BASE: ChartOption = {
  color: PALETTE,
  textStyle: { fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif', color: '#374151' },
  animationDuration: 300,
}

export default function Chart({ option, height = 200 }: { option: ChartOption; height?: number }) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!el.current) return
    const c = echarts.init(el.current, undefined, { renderer: 'canvas' })
    chart.current = c
    const ro = new ResizeObserver(() => c.resize())
    ro.observe(el.current)
    return () => {
      ro.disconnect()
      c.dispose()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption({ ...BASE, ...option }, { notMerge: true })
  }, [option])

  return <div ref={el} style={{ width: '100%', height }} />
}
