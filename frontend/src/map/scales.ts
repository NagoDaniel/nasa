import { scoreColor } from '../components/format'

export type Palette = 'blue' | 'red' | 'green' | 'brown' | 'div' | 'score'

const RAMPS: Record<Exclude<Palette, 'score'>, string[]> = {
  blue: ['#eff6ff', '#bfdbfe', '#60a5fa', '#2563eb', '#1e3a8a'],
  red: ['#fef9c3', '#fdba74', '#f97316', '#dc2626', '#7f1d1d'],
  green: ['#f7fee7', '#d9f99d', '#84cc16', '#4d7c0f', '#365314'],
  brown: ['#fdf6e3', '#e7d3a8', '#c69c6d', '#8b5e34', '#4a2f1a'],
  div: ['#8c510a', '#d8b365', '#f5f5f5', '#5ab4ac', '#01665e'], // dry (brown) → wet (teal)
}
export const NO_DATA = '#e5e7eb'

const hex = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16))
const mix = (a: string, b: string, t: number) => {
  const [x, y] = [hex(a), hex(b)]
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('')
}

export type Scale = { color: (v: number | null | undefined) => string; min: number; max: number; stops: string[]; discrete: boolean }

/** Colour scale over all values of a layer (every year), clamped to the 2nd–98th percentile. */
export function makeScale(values: number[], palette: Palette): Scale {
  if (palette === 'score') {
    return { color: (v) => (v === null || v === undefined ? NO_DATA : scoreColor(v)), min: 0, max: 100, stops: [15, 40, 60, 85].map(scoreColor), discrete: true }
  }
  const sorted = [...values].sort((a, b) => a - b)
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))))] ?? 0
  let min = q(0.02)
  let max = q(0.98)
  if (palette === 'div') {
    const m = Math.max(Math.abs(min), Math.abs(max)) || 1
    min = -m
    max = m
  }
  if (max === min) max = min + 1
  const ramp = RAMPS[palette]
  const color = (v: number | null | undefined) => {
    if (v === null || v === undefined || Number.isNaN(v)) return NO_DATA
    const t = Math.max(0, Math.min(1, (v - min) / (max - min))) * (ramp.length - 1)
    const i = Math.min(ramp.length - 2, Math.floor(t))
    return mix(ramp[i], ramp[i + 1], t - i)
  }
  return { color, min, max, stops: ramp, discrete: false }
}

/** Digits to show for a value of this magnitude. */
export const digitsFor = (max: number) => (Math.abs(max) < 3 ? 2 : Math.abs(max) < 30 ? 1 : 0)
