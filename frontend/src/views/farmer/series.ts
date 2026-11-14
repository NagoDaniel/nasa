import type { Indicator } from '../../api/types'

export const MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

/** Yearly totals (sum) or means of an indicator; `partial` marks incomplete years. */
export function yearly(ind: Indicator) {
  const by = new Map<number, number[]>()
  ind.keys.forEach((k, i) => {
    const v = ind.values[i]
    const y = Number(k.slice(0, 4))
    if (!by.has(y)) by.set(y, [])
    if (v !== null) by.get(y)!.push(v)
  })
  const steps = ind.period.step === 'month' ? 12 : 20
  return [...by.keys()].sort().map((y) => {
    const vs = by.get(y)!
    const total = vs.reduce((a, b) => a + b, 0)
    const value = vs.length === 0 ? null : ind.aggregation === 'sum' ? total : total / vs.length
    return { year: y, value, partial: vs.length < steps, n: vs.length }
  })
}

/** Average per calendar month over all years, and the latest year's months. */
export function monthly(ind: Indicator) {
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

/** Latest complete year and the average of all complete years. */
export function latestComplete(ind: Indicator | undefined) {
  if (!ind) return null
  const ys = yearly(ind).filter((y) => !y.partial && y.value !== null)
  if (!ys.length) return null
  const last = ys[ys.length - 1]
  const avg = ys.reduce((a, y) => a + (y.value as number), 0) / ys.length
  return { year: last.year, value: last.value as number, avg }
}
