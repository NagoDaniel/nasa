import { useEffect, useRef } from 'react'
import {
  AttributionControl,
  Map as MlMap,
  NavigationControl,
  ScaleControl,
  type MapGeoJSONFeature,
  type MapLayerMouseEvent,
  type StyleSpecification,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BASEMAP_URL,
  HIDDEN_BASEMAP_LAYERS,
  RO_BOUNDS,
  RO_MAX_BOUNDS,
  UNDER_ROADS_BEFORE,
  geoSource,
  lowLayers,
  terrainSource,
  topLayers,
} from './style'

export type AreaSelection =
  | { kind: 'county'; code: string; name: string; region: string; nuts2: string }
  | { kind: 'commune'; id: string; name: string; county: string; countyName: string; region: string }

type Props = {
  onSelect?: (sel: AreaSelection | null) => void
  initialCounty?: string
}

type FeatureRef = { source: 'counties' | 'communes'; id: string | number }

export default function RomaniaMap({ onSelect, initialCounty = 'AB' }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

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
        bounds: RO_BOUNDS,
        fitBoundsOptions: { padding: 24 },
        maxBounds: RO_MAX_BOUNDS,
        minZoom: 5.5,
        maxZoom: 15,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
      })
      map.touchZoomRotate.disableRotation()
      if (import.meta.env.DEV) (window as unknown as { __map: MlMap }).__map = map // debugging aid
      map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
      map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left')
      map.addControl(new AttributionControl({ compact: true }), 'bottom-right')

      let hovered: FeatureRef | null = null
      let selected: FeatureRef | null = null
      const setState = (ref: FeatureRef | null, state: Record<string, boolean>) => {
        if (ref) map!.setFeatureState(ref, state)
      }

      const pick = (e: MapLayerMouseEvent): FeatureRef & { f: MapGeoJSONFeature } | null => {
        const layers = map!.getZoom() >= 8 ? ['commune-fill', 'county-fill'] : ['county-fill']
        const f = map!.queryRenderedFeatures(e.point, { layers })[0]
        if (!f || f.id === undefined) return null
        return { source: f.source as FeatureRef['source'], id: f.id, f }
      }

      const select = (ref: (FeatureRef & { f?: MapGeoJSONFeature }) | null, props?: Record<string, string>) => {
        setState(selected, { selected: false })
        selected = ref
        setState(selected, { selected: true })
        if (!ref || !props) return onSelectRef.current?.(null)
        onSelectRef.current?.(
          ref.source === 'counties'
            ? { kind: 'county', code: props.code, name: props.name, region: props.region, nuts2: props.nuts2 }
            : { kind: 'commune', id: props.id, name: props.name, county: props.county, countyName: props.county_name, region: props.region },
        )
      }

      map.on('mousemove', (e) => {
        const hit = pick(e)
        if (hovered && (!hit || hit.id !== hovered.id || hit.source !== hovered.source)) {
          setState(hovered, { hover: false })
          hovered = null
        }
        if (hit && !hovered) {
          hovered = { source: hit.source, id: hit.id }
          setState(hovered, { hover: true })
        }
        map!.getCanvas().style.cursor = hit ? 'pointer' : ''
      })
      map.on('mouseout', () => {
        setState(hovered, { hover: false })
        hovered = null
      })
      map.on('click', (e) => {
        const hit = pick(e)
        select(hit, hit?.f.properties as Record<string, string> | undefined)
      })

      // Pre-select Alba once the counties source is loaded.
      const preselect = () => {
        if (!map!.isSourceLoaded('counties')) return
        map!.off('sourcedata', preselect)
        const f = map!.querySourceFeatures('counties', { filter: ['==', ['get', 'code'], initialCounty] })[0]
        if (f) select({ source: 'counties', id: initialCounty }, f.properties as Record<string, string>)
      }
      map.on('sourcedata', preselect)
    })()

    return () => {
      cancelled = true
      map?.remove()
    }
  }, [initialCounty])

  return <div ref={container} className="map" />
}
