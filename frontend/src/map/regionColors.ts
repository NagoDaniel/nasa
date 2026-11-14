import type { ExpressionSpecification } from 'maplibre-gl'

/** 8 development regions (NUTS-2) — atlas-style pastel hues. */
export const REGION_COLORS: Record<string, string> = {
  'Nord-Vest': '#e8b04b',
  Centru: '#7fb069',
  'Nord-Est': '#d98c8c',
  'Sud-Est': '#6fa8c9',
  'Sud-Muntenia': '#c9a0dc',
  'București-Ilfov': '#e07a5f',
  'Sud-Vest Oltenia': '#b8b05a',
  Vest: '#5fb3a1',
}

/** County code → region, so each county gets its own shade of its region's hue. */
export const COUNTY_REGION: Record<string, string> = {
  BH: 'Nord-Vest', BN: 'Nord-Vest', CJ: 'Nord-Vest', MM: 'Nord-Vest', SM: 'Nord-Vest', SJ: 'Nord-Vest',
  AB: 'Centru', BV: 'Centru', CV: 'Centru', HR: 'Centru', MS: 'Centru', SB: 'Centru',
  BC: 'Nord-Est', BT: 'Nord-Est', IS: 'Nord-Est', NT: 'Nord-Est', SV: 'Nord-Est', VS: 'Nord-Est',
  BR: 'Sud-Est', BZ: 'Sud-Est', CT: 'Sud-Est', GL: 'Sud-Est', TL: 'Sud-Est', VN: 'Sud-Est',
  AG: 'Sud-Muntenia', CL: 'Sud-Muntenia', DB: 'Sud-Muntenia', GR: 'Sud-Muntenia', IL: 'Sud-Muntenia', PH: 'Sud-Muntenia', TR: 'Sud-Muntenia',
  B: 'București-Ilfov', IF: 'București-Ilfov',
  DJ: 'Sud-Vest Oltenia', GJ: 'Sud-Vest Oltenia', MH: 'Sud-Vest Oltenia', OT: 'Sud-Vest Oltenia', VL: 'Sud-Vest Oltenia',
  AR: 'Vest', CS: 'Vest', HD: 'Vest', TM: 'Vest',
}

function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16)
  const ch = (v: number) => {
    const t = amount < 0 ? 0 : 255
    const p = Math.abs(amount)
    return Math.round((t - v) * p + v)
  }
  const r = ch((n >> 16) & 255), g = ch((n >> 8) & 255), b = ch(n & 255)
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`
}

const STEPS = [-0.18, 0.12, -0.06, 0.26, -0.28, 0.02, 0.38]

export function countyColor(code: string): string {
  const region = COUNTY_REGION[code]
  const siblings = Object.keys(COUNTY_REGION).filter((c) => COUNTY_REGION[c] === region).sort()
  return shade(REGION_COLORS[region] ?? '#999999', STEPS[siblings.indexOf(code) % STEPS.length])
}

/** MapLibre `match` expression: ["get","code"] → per-county colour. */
export const countyColorExpression: ExpressionSpecification = [
  'match',
  ['get', 'code'],
  ...Object.keys(COUNTY_REGION).flatMap((c) => [c, countyColor(c)]),
  '#cccccc',
] as unknown as ExpressionSpecification
