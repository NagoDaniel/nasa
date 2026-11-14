export const fmt = (v: number | null | undefined, nd = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? '–' : v.toLocaleString('en-US', { maximumFractionDigits: nd, minimumFractionDigits: nd })

export const scoreColor = (s: number | null | undefined) => {
  if (s === null || s === undefined) return '#cbd5e1'
  if (s >= 70) return '#16a34a'
  if (s >= 50) return '#ca8a04'
  if (s >= 30) return '#ea580c'
  return '#dc2626'
}
