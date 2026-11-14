import { createContext, useContext } from 'react'
import type { DrawMode, FieldOverlays, Ring } from '../map/draw'

/** Shared state between the "My field" panel and the map (drawing, overlays). */
export type FieldLinkCtx = {
  mode: DrawMode
  setMode: (m: DrawMode) => void
  /** Committed outline (after a drag / corner edit ends). */
  ring: Ring | null
  setRing: (r: Ring | null) => void
  /** Outline while it is being dragged (for the live area). */
  liveRing: Ring | null
  overlays: FieldOverlays
  setOverlays: (o: FieldOverlays) => void
  fitTo: (bbox: [number, number, number, number], maxZoom?: number) => void
}

export const FieldLink = createContext<FieldLinkCtx | null>(null)

export function useFieldLink(): FieldLinkCtx {
  const c = useContext(FieldLink)
  if (!c) throw new Error('useFieldLink outside provider')
  return c
}
