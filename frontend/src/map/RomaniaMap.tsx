import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import {
  AttributionControl,
  Map as MlMap,
  NavigationControl,
  ScaleControl,
  type ExpressionSpecification,
  type LngLatBoundsLike,
  type MapGeoJSONFeature,
  type MapMouseEvent,
  type StyleSpecification,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fmt } from '../components/format'
import type { ResolvedLayer } from '../state/MapLink'
import { FieldDrawer, type DrawMode, type FieldOverlays, type Ring } from './draw'
import { countyColorExpression } from './regionColors'
import { NO_DATA, digitsFor } from './scales'
import {
  AOI,
  BASEMAP_URL,
  COMMUNE_OPACITY,
  COUNTY_OPACITY,
  DATA_OPACITY,
  HIDDEN_BASEMAP_LAYERS,
  RO_BOUNDS,
  RO_MAX_BOUNDS,
  UNDER_ROADS_BEFORE,
  geoSource,
  lowLayers,
  terrainSource,
  topLayers,
} from './style'

export type MapPick = {
  id: string
  kind: 'county' | 'commune'
  name: string
  county: string
  countyName: string
  inAoi: boolean
}

export type MapHandle = {
  flyTo: (center: [number, number], zoom: number) => void
  fitBounds: (bbox: [number, number, number, number], maxZoom?: number) => void
}

type Props = {
  /** Selected area id (county code or commune id); the map only displays it. */
  selectedId: string | null
  onSelect?: (pick: MapPick) => void
  /** Area to outline (e.g. the table row under the mouse). */
  highlightId?: string | null
  onHover?: (id: string | null) => void
  /** Data to colour the areas by; null = plain region colours. */
  layer?: ResolvedLayer | null
  initialBounds?: LngLatBoundsLike
  outsideLabel?: string
  noDataLabel?: string
  /** Shown when a commune displays its county's value. */
  countyFigureLabel?: string
  /** Field drawing (farmer "My field" section). */
  drawMode?: DrawMode
  fieldRing?: Ring | null
  onFieldChange?: (ring: Ring | null, final: boolean) => void
  fieldOverlays?: FieldOverlays
  onSavedFieldClick?: (id: number) => void
}

type FeatureRef = { source: 'counties' | 'communes'; id: string }
const refOf = (id: string): FeatureRef => ({ source: id.includes('-') ? 'communes' : 'counties', id })
const match = (prop: string, pairs: string[]): ExpressionSpecification | string =>
  pairs.length ? (['match', ['get', prop], ...pairs, NO_DATA] as unknown as ExpressionSpecification) : NO_DATA

const RomaniaMap = forwardRef<MapHandle, Props>(function RomaniaMap(
  { selectedId, onSelect, highlightId = null, onHover, layer = null, initialBounds = RO_BOUNDS, outsideLabel = 'Outside study area', noDataLabel = 'no data', countyFigureLabel = 'county figure',
    drawMode = 'off', fieldRing = null, onFieldChange, fieldOverlays, onSavedFieldClick },
  handle,
) {
  const container = useRef<HTMLDivElement>(null)
  const tip = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MlMap | null>(null)
  const [ready, setReady] = useState(false)
  const latest = useRef({ onSelect, onHover, layer, outsideLabel, noDataLabel, countyFigureLabel, onFieldChange, onSavedFieldClick })
  latest.current = { onSelect, onHover, layer, outsideLabel, noDataLabel, countyFigureLabel, onFieldChange, onSavedFieldClick }
  const drawer = useRef<FieldDrawer | null>(null)
  const shown = useRef<{ selected: FeatureRef | null; highlight: FeatureRef | null; hover: FeatureRef | null }>({ selected: null, highlight: null, hover: null })

  useImperativeHandle(handle, () => ({
    flyTo: (center, zoom) => mapRef.current?.easeTo({ center, zoom, duration: 700 }),
    fitBounds: (b, maxZoom = 16.5) => mapRef.current?.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom, duration: 700 }),
  }), [])

  useEffect(() => {
    if (!container.current) return
    let cancelled = false
    let map: MlMap | undefined

    ;(async () => {
      const base = (await (await fetch(BASEMAP_URL)).json()) as StyleSpecification
      if (cancelled || !container.current) return

      // Drop OSM admin lines/country labels — our precise boundaries replace them.
      base.layers = base.layers.filter((l) => !HIDDEN_BASEMAP_LAYERS.includes(l.id))
      base.sources = {
        ...base.sources,
        terrain: terrainSource,
        mask: geoSource('/api/geo/mask'),
        outline: geoSource('/api/geo/outline'),
        regions: geoSource('/api/geo/regions'),
        counties: geoSource('/api/geo/counties', 'code'),
        communes: geoSource('/api/geo/communes', 'id'),
        labels: geoSource('/api/geo/labels'),
      }
      const at = base.layers.findIndex((l) => l.id === UNDER_ROADS_BEFORE)
      base.layers.splice(at < 0 ? base.layers.length : at, 0, ...lowLayers)
      base.layers.push(...topLayers)

      map = new MlMap({
        container: container.current,
        style: base,
        bounds: initialBounds,
        fitBoundsOptions: { padding: 24 },
        maxBounds: RO_MAX_BOUNDS,
        minZoom: 5.5,
        maxZoom: 18,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
      })
      const m = map
      m.touchZoomRotate.disableRotation()
      if (import.meta.env.DEV) (window as unknown as { __map: MlMap }).__map = m // debugging aid
      mapRef.current = m
      m.addControl(new NavigationControl({ showCompass: false }), 'top-right')
      m.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')
      m.addControl(new AttributionControl({ compact: true }), 'bottom-right')
      m.once('load', () => {
        if (cancelled) return
        // Start the compact attribution collapsed (it covers half the map on phones).
        container.current?.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
        drawer.current = new FieldDrawer(m, (r, final) => latest.current.onFieldChange?.(r, final), (id) => latest.current.onSavedFieldClick?.(id))
        setReady(true)
      })
      // The pane can change size (sidebar / data panel open-close).
      const ro = new ResizeObserver(() => m.resize())
      ro.observe(container.current)
      m.once('remove', () => ro.disconnect())

      const pick = (e: MapMouseEvent): MapGeoJSONFeature | null => {
        const layers = m.getZoom() >= 8 ? ['commune-fill', 'county-fill'] : ['county-fill']
        const f = m.queryRenderedFeatures(e.point, { layers })[0]
        return f && f.id !== undefined ? f : null
      }
      const setHover = (ref: FeatureRef | null) => {
        const cur = shown.current.hover
        if (cur?.id === ref?.id) return
        if (cur && cur.id !== shown.current.highlight?.id) m.setFeatureState(cur, { hover: false })
        if (ref) m.setFeatureState(ref, { hover: true })
        shown.current.hover = ref
        latest.current.onHover?.(ref?.id ?? null)
      }

      m.on('mousemove', (e) => {
        if (drawer.current?.busy()) {
          setHover(null)
          if (tip.current) tip.current.style.display = 'none'
          return
        }
        const f = pick(e)
        const el = tip.current
        if (!f) {
          setHover(null)
          m.getCanvas().style.cursor = ''
          if (el) el.style.display = 'none'
          return
        }
        const id = String(f.id)
        setHover(refOf(id))
        m.getCanvas().style.cursor = 'pointer'
        if (el) {
          const p = f.properties as Record<string, string>
          const l = latest.current.layer
          const inAoi = AOI.includes(p.county ?? p.code)
          let line = ''
          if (!inAoi) line = latest.current.outsideLabel
          else if (l) {
            // County-level layers (e.g. procurement scores from county statistics): a commune shows its county's value.
            const viaCounty = l.level === 'county' && id.includes('-')
            const v = l.values[viaCounty ? p.county : id]
            line = v === null || v === undefined
              ? `${l.label}: ${latest.current.noDataLabel}`
              : `${l.label}: <b>${fmt(v, digitsFor(l.scale.max))} ${l.unit}</b>${viaCounty ? ` <span class="map-tip-note">(${latest.current.countyFigureLabel})</span>` : ''}`
          }
          el.innerHTML = `<div class="map-tip-name"></div><div class="map-tip-val">${line}</div>`
          ;(el.firstChild as HTMLElement).textContent = p.county_name ? `${p.name} · ${p.county_name}` : p.name
          el.style.display = 'block'
          const w = m.getContainer().clientWidth
          el.style.left = `${Math.min(e.point.x + 14, w - el.offsetWidth - 6)}px`
          el.style.top = `${Math.max(6, e.point.y - el.offsetHeight - 10)}px`
        }
      })
      m.on('mouseout', () => {
        setHover(null)
        if (tip.current) tip.current.style.display = 'none'
      })
      m.on('click', (e) => {
        if (drawer.current?.busy()) return
        const f = pick(e)
        if (!f) return
        const p = f.properties as Record<string, string>
        const isCommune = f.source === 'communes'
        const county = isCommune ? p.county : p.code
        latest.current.onSelect?.({
          id: String(f.id),
          kind: isCommune ? 'commune' : 'county',
          name: p.name,
          county,
          countyName: isCommune ? p.county_name : p.name,
          inAoi: AOI.includes(county),
        })
      })
    })()

    return () => {
      cancelled = true
      mapRef.current = null
      shown.current = { selected: null, highlight: null, hover: null }
      setReady(false)
      drawer.current?.destroy()
      drawer.current = null
      map?.remove()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Field drawing state and overlays.
  useEffect(() => {
    if (ready) drawer.current?.setMode(drawMode)
  }, [drawMode, ready])
  useEffect(() => {
    if (ready) drawer.current?.setRing(fieldRing)
  }, [fieldRing, ready])
  useEffect(() => {
    if (ready) drawer.current?.setOverlays(fieldOverlays ?? {})
  }, [fieldOverlays, ready])

  // Selected area outline.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const prev = shown.current.selected
    if (prev) map.setFeatureState(prev, { selected: false })
    const next = selectedId ? refOf(selectedId) : null
    if (next) map.setFeatureState(next, { selected: true })
    shown.current.selected = next
  }, [selectedId, ready])

  // Outline of the area hovered elsewhere in the UI (table rows).
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const prev = shown.current.highlight
    if (prev && prev.id !== shown.current.hover?.id) map.setFeatureState(prev, { hover: false })
    const next = highlightId ? refOf(highlightId) : null
    if (next) map.setFeatureState(next, { hover: true })
    shown.current.highlight = next
  }, [highlightId, ready])

  // Colour areas by the active data layer, or fall back to region colours.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready || !map.getLayer('county-fill')) return
    if (!layer) {
      map.setPaintProperty('county-fill', 'fill-color', countyColorExpression)
      map.setPaintProperty('county-fill', 'fill-opacity', COUNTY_OPACITY)
      map.setPaintProperty('commune-fill', 'fill-color', '#1d4ed8')
      map.setPaintProperty('commune-fill', 'fill-opacity', COMMUNE_OPACITY)
      return
    }
    const counties: string[] = []
    const communes: string[] = []
    for (const [id, v] of Object.entries(layer.values)) {
      ;(id.includes('-') ? communes : counties).push(id, layer.scale.color(v))
    }
    map.setPaintProperty('county-fill', 'fill-color', match('code', counties))
    if (layer.level === 'commune') {
      // communes carry the colour; counties stay as outlines
      map.setPaintProperty('county-fill', 'fill-opacity', 0)
      map.setPaintProperty('commune-fill', 'fill-color', match('id', communes))
      map.setPaintProperty('commune-fill', 'fill-opacity', DATA_OPACITY)
    } else {
      map.setPaintProperty('county-fill', 'fill-opacity', DATA_OPACITY)
      map.setPaintProperty('commune-fill', 'fill-color', '#1d4ed8')
      map.setPaintProperty('commune-fill', 'fill-opacity', COMMUNE_OPACITY)
    }
  }, [layer, ready])

  return (
    <div className="map-wrap">
      <div ref={container} className="map" />
      <div ref={tip} className="map-tip" style={{ display: 'none' }} />
    </div>
  )
})

export default RomaniaMap
