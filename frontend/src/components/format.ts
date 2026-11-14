/** Number style follows the UI language (set by the I18nProvider): 1,234.5 (EN) / 1.234,5 (RO). */
let numLocale = 'en-US'
export const setNumberLocale = (lang: 'en' | 'ro') => {
  numLocale = lang === 'ro' ? 'ro-RO' : 'en-US'
}

export const fmt = (v: number | null | undefined, nd = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? '–' : v.toLocaleString(numLocale, { maximumFractionDigits: nd, minimumFractionDigits: nd, useGrouping: true })

export const scoreColor = (s: number | null | undefined) => {
  if (s === null || s === undefined) return '#cbd5e1'
  if (s >= 70) return '#16a34a'
  if (s >= 50) return '#ca8a04'
  if (s >= 30) return '#ea580c'
  return '#dc2626'
}
