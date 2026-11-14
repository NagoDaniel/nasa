import { createContext, useContext } from 'react'
import type { Scale } from '../map/scales'

/** Which data the map is coloured by. */
export type LayerSpec = { kind: 'indicator' | 'agro' | 'soil' | 'cropshare'; key: string }

/** A layer resolved to one value per area, ready to draw. */
export type ResolvedLayer = {
  label: string
  unit: string
  values: Record<string, number | null>
  scale: Scale
  /** 'commune' = communes and counties have values; 'county' = counties only. */
  level: 'commune' | 'county'
  source?: string
}

export type MapLinkCtx = {
  /** Data layer shown on the map (farmer sections). */
  spec: LayerSpec | null
  setSpec: (s: LayerSpec | null, year?: string) => void
  year: string | null
  setYear: (y: string) => void
  years: string[] | null
  /** Layer computed by a view itself (procurement scores). */
  setCustomLayer: (l: ResolvedLayer | null) => void
  /** Area hovered in a table or list: outlined on the map. */
  setHighlight: (id: string | null) => void
  /** Area hovered on the map: lets tables highlight the matching row. */
  hoveredOnMap: string | null
  /** Select an area from the data side (flies the map there). */
  selectArea: (id: string) => void
  goTo: (section: string) => void
}

export const MapLink = createContext<MapLinkCtx | null>(null)

export function useMapLink(): MapLinkCtx {
  const c = useContext(MapLink)
  if (!c) throw new Error('useMapLink outside provider')
  return c
}

export const sameSpec = (a: LayerSpec | null, b: LayerSpec | null) => !!a && !!b && a.kind === b.kind && a.key === b.key
