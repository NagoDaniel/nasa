import type { AssistantAction, Unit } from '../api/types'
import { B_CROPS } from '../i18n/names'
import type { MapLinkCtx } from '../state/MapLink'
import { SECTIONS } from '../state/sections'

const ALL_SECTIONS: readonly string[] = [...SECTIONS.farmer, ...SECTIONS.procurement]
const KINDS = ['indicator', 'agro', 'soil', 'cropshare'] as const
const METRICS = ['availability', 'quality', 'impact'] as const
const ORDER: AssistantAction['type'][] = ['select_area', 'open_section', 'color_map', 'set_procurement_crop']

type Deps = Pick<MapLinkCtx, 'selectArea' | 'goTo' | 'runCommand'> & { byId: Map<string, Unit> }

/**
 * Run the dashboard actions returned with a reply. The server already validated them;
 * they are checked again here against what the dashboard knows, anything else is ignored.
 * Returns how many were applied.
 */
export function applyActions(actions: AssistantAction[], d: Deps): number {
  let n = 0
  const sorted = [...actions].slice(0, 3).sort((a, b) => ORDER.indexOf(a.type) - ORDER.indexOf(b.type))
  const opensSection = sorted.some((a) => a.type === 'open_section')
  for (const a of sorted) {
    if (a.type === 'select_area' && d.byId.has(a.unit_id)) {
      d.selectArea(a.unit_id)
      n++
    } else if (a.type === 'open_section' && ALL_SECTIONS.includes(a.section)) {
      d.goTo(a.section)
      n++
    } else if (
      a.type === 'color_map' && (KINDS as readonly string[]).includes(a.kind) && /^[a-z0-9_]{1,40}$/.test(a.key) &&
      (!a.year || /^\d{4}$/.test(a.year))
    ) {
      d.runCommand({ type: 'layer', spec: { kind: a.kind, key: a.key }, year: a.year ?? null })
      n++
    } else if (a.type === 'set_procurement_crop' && (B_CROPS as readonly string[]).includes(a.crop)) {
      if (!opensSection) d.goTo('sourcing')
      const metric = a.metric && (METRICS as readonly string[]).includes(a.metric) ? a.metric : null
      d.runCommand({ type: 'procurement', crop: a.crop, metric })
      n++
    }
  }
  return n
}
