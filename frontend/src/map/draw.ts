import type { FeatureCollection, Polygon } from 'geojson'
import type { GeoJSONSource, ImageSource, Map as MlMap, MapLayerMouseEvent, MapLayerTouchEvent, MapMouseEvent, MapTouchEvent, PointLike } from 'maplibre-gl'

export type DrawMode = 'off' | 'rect' | 'poly' | 'edit'
export type Ring = [number, number][] // open ring (first point not repeated)

export type FieldOverlays = {
  cells?: FeatureCollection | null
  soil?: FeatureCollection | null
  image?: { url: string; corners: [number, number][] } | null
  saved?: FeatureCollection | null
  satellite?: boolean
}

/** Approximate geodesic area (ha) on the sphere; the backend gives the exact WGS84 value. */
export function ringAreaHa(ring: Ring): number {
  if (ring.length < 3) return 0
  const R = 6378137
  const rad = Math.PI / 180
  let s = 0
  for (let i = 0; i < ring.length; i++) {
    const [l1, p1] = ring[i]
    const [l2, p2] = ring[(i + 1) % ring.length]
    s += (l2 - l1) * rad * (2 + Math.sin(p1 * rad) + Math.sin(p2 * rad))
  }
  return Math.abs((s * R * R) / 2) / 10_000
}

export const toPolygon = (ring: Ring): Polygon => ({ type: 'Polygon', coordinates: [[...ring, ring[0]]] })
export const fromPolygon = (p: Polygon): Ring => p.coordinates[0].slice(0, -1).map(([x, y]) => [x, y])

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }
const SAT_URL = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg'
const SAT_ATTR = 'Sentinel-2 cloudless 2023 by <a href="https://s2maps.eu" target="_blank" rel="noopener">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2023)'
const BLANK_IMG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='

/**
 * Drawing and editing one field outline on a MapLibre map:
 *  - rect: press and drag a box, like selecting on a desktop (touch: drag with one finger)
 *  - poly: click corners; click the first corner, double-click or press Enter to finish;
 *          Backspace removes the last corner, Escape cancels
 *  - edit: drag corners; drag the small mid-edge handles to add a corner;
 *          right-click (or long-press) a corner to delete it
 * Also draws the field-related overlays (grid cells, soil pixels, NDVI image, saved fields).
 */
export class FieldDrawer {
  private mode: DrawMode = 'off'
  private ring: Ring | null = null
  private draft: Ring = []
  private hover: [number, number] | null = null
  private rectStart: { x: number; y: number } | null = null
  private dragIdx: number | null = null
  private longPress: number | undefined
  private hasImage = false

  private map: MlMap
  private onChange: (ring: Ring | null, final: boolean) => void
  private onSavedClick?: (id: number) => void

  constructor(map: MlMap, onChange: (ring: Ring | null, final: boolean) => void, onSavedClick?: (id: number) => void) {
    this.map = map
    this.onChange = onChange
    this.onSavedClick = onSavedClick
    const m = map
    m.addSource('f-sat', { type: 'raster', tiles: [SAT_URL], tileSize: 256, maxzoom: 15, attribution: SAT_ATTR })
    m.addLayer({ id: 'f-sat', type: 'raster', source: 'f-sat', layout: { visibility: 'none' }, paint: { 'raster-opacity': 1 } }, 'commune-line')
    m.addSource('f-img', { type: 'image', url: BLANK_IMG, coordinates: [[0, 1], [1, 1], [1, 0], [0, 0]] })
    m.addLayer({ id: 'f-img', type: 'raster', source: 'f-img', layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.92, 'raster-resampling': 'nearest', 'raster-fade-duration': 0 } })
    for (const id of ['f-cells', 'f-soil', 'f-saved', 'f-field', 'f-verts', 'f-mids', 'f-draft']) m.addSource(id, { type: 'geojson', data: EMPTY })
    m.addLayer({ id: 'f-cells-line', type: 'line', source: 'f-cells', paint: { 'line-color': '#7c3aed', 'line-width': 2, 'line-dasharray': [3, 2] } })
    m.addLayer({
      id: 'f-cells-label', type: 'symbol', source: 'f-cells', filter: ['==', ['geometry-type'], 'Point'],
      layout: { 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-max-width': 14, 'text-allow-overlap': false },
      paint: { 'text-color': '#5b21b6', 'text-halo-color': '#fff', 'text-halo-width': 1.6 },
    })
    m.addLayer({ id: 'f-soil-line', type: 'line', source: 'f-soil', paint: { 'line-color': '#92400e', 'line-width': 1.5 } })
    m.addLayer({ id: 'f-saved-fill', type: 'fill', source: 'f-saved', paint: { 'fill-color': '#0ea5e9', 'fill-opacity': 0.12 } })
    m.addLayer({ id: 'f-saved-line', type: 'line', source: 'f-saved', paint: { 'line-color': '#0369a1', 'line-width': 1.5 } })
    m.addLayer({ id: 'f-field-fill', type: 'fill', source: 'f-field', paint: { 'fill-color': '#facc15', 'fill-opacity': ['case', ['boolean', ['get', 'image'], false], 0, 0.18] } })
    m.addLayer({ id: 'f-field-halo', type: 'line', source: 'f-field', paint: { 'line-color': '#fff', 'line-width': 5 } })
    m.addLayer({ id: 'f-field-line', type: 'line', source: 'f-field', paint: { 'line-color': '#ca8a04', 'line-width': 2.5 } })
    m.addLayer({ id: 'f-draft-fill', type: 'fill', source: 'f-draft', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#38bdf8', 'fill-opacity': 0.2 } })
    m.addLayer({ id: 'f-draft-line', type: 'line', source: 'f-draft', paint: { 'line-color': '#0284c7', 'line-width': 2, 'line-dasharray': [2, 1.5] } })
    m.addLayer({ id: 'f-draft-pts', type: 'circle', source: 'f-draft', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 5, 'circle-color': '#fff', 'circle-stroke-color': '#0284c7', 'circle-stroke-width': 2 } })
    m.addLayer({ id: 'f-mids', type: 'circle', source: 'f-mids', paint: { 'circle-radius': 4.5, 'circle-color': '#ca8a04', 'circle-opacity': 0.75, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 } })
    m.addLayer({ id: 'f-verts', type: 'circle', source: 'f-verts', paint: { 'circle-radius': 7, 'circle-color': '#fff', 'circle-stroke-color': '#ca8a04', 'circle-stroke-width': 2.5 } })

    m.on('mousedown', this.onDown)
    m.on('touchstart', this.onDown)
    m.on('mousemove', this.onMove)
    m.on('touchmove', this.onMove)
    m.on('mouseup', this.onUp)
    m.on('touchend', this.onUp)
    m.on('click', this.onClick)
    m.on('dblclick', this.onDbl)
    m.on('mousedown', 'f-verts', this.onVertexDown)
    m.on('touchstart', 'f-verts', this.onVertexDown)
    m.on('mousedown', 'f-mids', this.onMidDown)
    m.on('touchstart', 'f-mids', this.onMidDown)
    m.on('contextmenu', 'f-verts', this.onVertexDelete)
    m.on('mouseenter', 'f-verts', this.pointer)
    m.on('mouseleave', 'f-verts', this.unpointer)
    m.on('mouseenter', 'f-mids', this.pointer)
    m.on('mouseleave', 'f-mids', this.unpointer)
    m.on('click', 'f-saved-fill', this.onSaved)
    window.addEventListener('keydown', this.onKey)
  }

  destroy() {
    window.removeEventListener('keydown', this.onKey)
  }

  /** True while a draw/edit interaction should suppress area selection on click. */
  busy() {
    return this.mode !== 'off'
  }

  setMode(mode: DrawMode) {
    if (mode === this.mode) return
    this.mode = mode
    this.draft = []
    this.rectStart = null
    this.dragIdx = null
    const drawing = mode === 'rect' || mode === 'poly'
    if (drawing) {
      this.map.dragPan.disable()
      this.map.doubleClickZoom.disable()
      this.map.boxZoom.disable()
    } else {
      this.map.dragPan.enable()
      this.map.doubleClickZoom.enable()
      this.map.boxZoom.enable()
    }
    this.map.getCanvas().style.cursor = drawing ? 'crosshair' : ''
    this.render()
  }

  setRing(ring: Ring | null) {
    this.ring = ring && ring.length >= 3 ? ring.map((p) => [p[0], p[1]]) : null
    this.render()
  }

  setOverlays(o: FieldOverlays) {
    const m = this.map
    ;(m.getSource('f-cells') as GeoJSONSource).setData(o.cells ?? EMPTY)
    ;(m.getSource('f-soil') as GeoJSONSource).setData(o.soil ?? EMPTY)
    ;(m.getSource('f-saved') as GeoJSONSource).setData(o.saved ?? EMPTY)
    m.setLayoutProperty('f-sat', 'visibility', o.satellite ? 'visible' : 'none')
    const img = m.getSource('f-img') as ImageSource
    if (o.image) {
      img.updateImage({ url: o.image.url, coordinates: o.image.corners as [[number, number], [number, number], [number, number], [number, number]] })
      m.setLayoutProperty('f-img', 'visibility', 'visible')
    } else {
      m.setLayoutProperty('f-img', 'visibility', 'none')
    }
    this.hasImage = !!o.image
    this.render()
  }

  // ------------------------------------------------------------------ rendering
  private render() {
    const m = this.map
    const ring = this.ring
    const field: FeatureCollection = ring
      ? { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { image: this.hasImage }, geometry: toPolygon(ring) }] }
      : EMPTY
    ;(m.getSource('f-field') as GeoJSONSource).setData(field)
    const editing = this.mode === 'edit' && ring
    ;(m.getSource('f-verts') as GeoJSONSource).setData(editing
      ? { type: 'FeatureCollection', features: ring.map((p, i) => ({ type: 'Feature', properties: { i }, geometry: { type: 'Point', coordinates: p } })) }
      : EMPTY)
    ;(m.getSource('f-mids') as GeoJSONSource).setData(editing
      ? {
          type: 'FeatureCollection',
          features: ring.map((p, i) => {
            const q = ring[(i + 1) % ring.length]
            return { type: 'Feature', properties: { i }, geometry: { type: 'Point', coordinates: [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2] } }
          }),
        }
      : EMPTY)
    const d = this.hover && this.mode === 'poly' ? [...this.draft, this.hover] : this.draft
    const feats: FeatureCollection['features'] = this.draft.map((p) => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: p } }))
    if (d.length >= 3) feats.push({ type: 'Feature', properties: {}, geometry: toPolygon(d as Ring) })
    else if (d.length === 2) feats.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: d } })
    ;(m.getSource('f-draft') as GeoJSONSource).setData({ type: 'FeatureCollection', features: feats })
  }

  private rectRing(a: { x: number; y: number }, b: { x: number; y: number }): Ring {
    const pts: PointLike[] = [[a.x, a.y], [b.x, a.y], [b.x, b.y], [a.x, b.y]]
    const ring = pts.map((p) => {
      const ll = this.map.unproject(p)
      return [ll.lng, ll.lat] as [number, number]
    })
    // counter-clockwise on the map = clockwise on screen when y grows downward: normalise
    return ringAreaSigned(ring) < 0 ? ring.reverse() : ring
  }

  // ------------------------------------------------------------------ events
  private onDown = (e: MapMouseEvent | MapTouchEvent) => {
    if (this.mode !== 'rect') return
    if ('points' in e && e.points.length !== 1) return
    if ('originalEvent' in e && (e.originalEvent as MouseEvent).button > 0) return
    e.preventDefault()
    this.rectStart = { x: e.point.x, y: e.point.y }
  }

  private onMove = (e: MapMouseEvent | MapTouchEvent) => {
    if (this.mode === 'rect' && this.rectStart) {
      this.draft = this.rectRing(this.rectStart, e.point)
      this.render()
    } else if (this.mode === 'poly') {
      this.hover = [e.lngLat.lng, e.lngLat.lat]
      if (this.draft.length) this.render()
    } else if (this.mode === 'edit' && this.dragIdx !== null && this.ring) {
      e.preventDefault()
      window.clearTimeout(this.longPress)
      this.ring[this.dragIdx] = [e.lngLat.lng, e.lngLat.lat]
      this.render()
      this.onChange(this.ring.slice(), false)
    }
  }

  private onUp = (e: MapMouseEvent | MapTouchEvent) => {
    window.clearTimeout(this.longPress)
    if (this.mode === 'rect' && this.rectStart) {
      const a = this.rectStart
      const b = e.point ?? a
      this.rectStart = null
      this.draft = []
      if (Math.abs(b.x - a.x) > 6 && Math.abs(b.y - a.y) > 6) {
        this.ring = this.rectRing(a, b)
        this.onChange(this.ring.slice(), true)
      }
      this.render()
    } else if (this.mode === 'edit' && this.dragIdx !== null) {
      this.dragIdx = null
      this.map.dragPan.enable()
      if (this.ring) this.onChange(this.ring.slice(), true)
    }
  }

  private onClick = (e: MapMouseEvent) => {
    if (this.mode !== 'poly') return
    const p: [number, number] = [e.lngLat.lng, e.lngLat.lat]
    if (this.draft.length >= 3) {
      const first = this.map.project(this.draft[0])
      if (Math.hypot(first.x - e.point.x, first.y - e.point.y) < 12) return this.finishPoly()
    }
    const last = this.draft[this.draft.length - 1]
    if (last) {
      const lp = this.map.project(last)
      if (Math.hypot(lp.x - e.point.x, lp.y - e.point.y) < 4) return // second click of a double-click
    }
    this.draft.push(p)
    this.render()
  }

  private onDbl = (e: MapMouseEvent) => {
    if (this.mode !== 'poly') return
    e.preventDefault()
    this.finishPoly()
  }

  private finishPoly() {
    if (this.draft.length < 3) return
    this.ring = this.draft.slice()
    this.draft = []
    this.hover = null
    this.onChange(this.ring.slice(), true)
    this.render()
  }

  private onKey = (e: KeyboardEvent) => {
    const t = e.target as HTMLElement | null
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
    if (this.mode === 'poly') {
      if (e.key === 'Escape') {
        this.draft = []
        this.render()
      } else if (e.key === 'Backspace') {
        this.draft.pop()
        this.render()
      } else if (e.key === 'Enter') this.finishPoly()
    } else if (this.mode === 'rect' && e.key === 'Escape') {
      this.rectStart = null
      this.draft = []
      this.render()
    }
  }

  private onVertexDown = (e: MapLayerMouseEvent | MapLayerTouchEvent) => {
    if (this.mode !== 'edit' || !this.ring || !e.features?.length) return
    e.preventDefault()
    this.map.dragPan.disable()
    const i = Number(e.features[0].properties?.i)
    this.dragIdx = i
    if ('points' in e) this.longPress = window.setTimeout(() => this.deleteVertex(i), 650)
  }

  private onMidDown = (e: MapLayerMouseEvent | MapLayerTouchEvent) => {
    if (this.mode !== 'edit' || !this.ring || !e.features?.length) return
    e.preventDefault()
    this.map.dragPan.disable()
    const i = Number(e.features[0].properties?.i)
    this.ring.splice(i + 1, 0, [e.lngLat.lng, e.lngLat.lat])
    this.dragIdx = i + 1
    this.render()
  }

  private onVertexDelete = (e: MapLayerMouseEvent) => {
    if (this.mode !== 'edit' || !e.features?.length) return
    e.preventDefault()
    this.deleteVertex(Number(e.features[0].properties?.i))
  }

  private deleteVertex(i: number) {
    if (!this.ring || this.ring.length <= 3) return
    this.dragIdx = null
    this.map.dragPan.enable()
    this.ring.splice(i, 1)
    this.render()
    this.onChange(this.ring.slice(), true)
  }

  private onSaved = (e: MapLayerMouseEvent) => {
    if (this.mode === 'rect' || this.mode === 'poly') return
    const id = Number(e.features?.[0]?.properties?.id)
    if (Number.isFinite(id)) this.onSavedClick?.(id)
  }

  private pointer = () => {
    if (this.mode === 'edit') this.map.getCanvas().style.cursor = 'grab'
  }

  private unpointer = () => {
    if (this.mode === 'edit') this.map.getCanvas().style.cursor = ''
  }
}

function ringAreaSigned(ring: Ring): number {
  let s = 0
  for (let i = 0; i < ring.length; i++) {
    const [x1, y1] = ring[i]
    const [x2, y2] = ring[(i + 1) % ring.length]
    s += x1 * y2 - x2 * y1
  }
  return s / 2
}
