import type { ExpressionSpecification, LayerSpecification, LngLatBoundsLike, RasterDEMSourceSpecification, StyleSpecification } from 'maplibre-gl'
import { countyColorExpression } from './regionColors'

export const BASEMAP_URL = 'https://tiles.openfreemap.org/styles/liberty'

/** Romania bbox (lon/lat) with a little breathing room. */
export const RO_BOUNDS: LngLatBoundsLike = [[20.2, 43.6], [29.8, 48.3]]
export const RO_MAX_BOUNDS: LngLatBoundsLike = [[18.2, 42.6], [31.8, 49.3]]

export const MASK_COLOR = '#eef1f4'
/** Study area: Alba + neighbouring counties (the only ones with processed data). */
export const AOI = ['AB', 'AR', 'BH', 'CJ', 'HD', 'MS', 'SB', 'VL']
const FONT_REG = ['Noto Sans Regular']
const FONT_BOLD = ['Noto Sans Bold']
const FONT_ITALIC = ['Noto Sans Italic']

/** Basemap layers we hide: OSM admin lines/labels are replaced by our precise ones. */
export const HIDDEN_BASEMAP_LAYERS = [
  'boundary_3', 'boundary_2', 'boundary_disputed',
  'label_state', 'label_country_1', 'label_country_2', 'label_country_3',
  'building-3d',
]

/** Insert our tint + hillshade under water/roads so the basemap stays readable. */
export const UNDER_ROADS_BEFORE = 'waterway_tunnel'

export const terrainSource: RasterDEMSourceSpecification = {
  type: 'raster-dem',
  tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
  encoding: 'terrarium',
  tileSize: 256,
  maxzoom: 13,
  attribution: 'Terrain: <a href="https://registry.opendata.aws/terrain-tiles/">Mapzen/AWS Terrain Tiles</a>',
}

const GB_ATTR = 'Boundaries: <a href="https://www.geoboundaries.org">geoBoundaries</a> (ANCPI, World Bank, CC BY 4.0)'

export function geoSource(url: string, promoteId?: string) {
  return {
    type: 'geojson' as const,
    data: url,
    attribution: GB_ATTR,
    ...(promoteId ? { promoteId } : {}),
  }
}

function countyOpacity(base: number): ExpressionSpecification {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false], Math.max(0.5, base + 0.25),
    ['boolean', ['feature-state', 'hover'], false], Math.max(0.42, base + 0.18),
    base,
  ]
}

// zoom must be the top-level input, so the hover/selected case sits inside each stop
export const COUNTY_OPACITY: ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'],
  6, countyOpacity(0.32),
  9, countyOpacity(0.18),
  12, countyOpacity(0.08),
]
export const CHOROPLETH_OPACITY: ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'],
  6, countyOpacity(0.7),
  9, countyOpacity(0.45),
  12, countyOpacity(0.2),
]

/** Layers placed low in the stack (under roads / water / labels). */
export const lowLayers: LayerSpecification[] = [
  {
    id: 'hillshade',
    type: 'hillshade',
    source: 'terrain',
    paint: {
      'hillshade-exaggeration': 0.45,
      'hillshade-shadow-color': '#4a4a4a',
      'hillshade-highlight-color': '#ffffff',
      'hillshade-accent-color': '#5a5a5a',
    },
  },
  {
    id: 'county-fill',
    type: 'fill',
    source: 'counties',
    paint: {
      'fill-color': countyColorExpression,
      'fill-opacity': COUNTY_OPACITY,
    },
  },
  {
    id: 'county-outside',
    type: 'fill',
    source: 'counties',
    filter: ['!', ['in', ['get', 'code'], ['literal', AOI]]],
    paint: { 'fill-color': '#e5e7eb', 'fill-opacity': 0.55 },
  },
  {
    id: 'commune-fill',
    type: 'fill',
    source: 'communes',
    minzoom: 8,
    paint: {
      'fill-color': '#1d4ed8',
      'fill-opacity': [
        'case',
        ['boolean', ['feature-state', 'selected'], false], 0.28,
        ['boolean', ['feature-state', 'hover'], false], 0.14,
        0,
      ],
    },
  },
]

/** Layers on top of everything (mask hides the world outside Romania). */
export const topLayers: LayerSpecification[] = [
  { id: 'mask', type: 'fill', source: 'mask', paint: { 'fill-color': MASK_COLOR, 'fill-opacity': 1 } },
  {
    id: 'commune-line',
    type: 'line',
    source: 'communes',
    minzoom: 7.5,
    paint: {
      'line-color': '#5b3f7a',
      'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.8, 12, 1.8],
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 7.5, 0, 8.3, 0.85],
      'line-dasharray': [4, 2],
    },
  },
  {
    id: 'county-line',
    type: 'line',
    source: 'counties',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': '#5b5b6b',
      'line-width': ['interpolate', ['linear'], ['zoom'], 5.5, 0.6, 8, 1.3, 12, 2.4],
    },
  },
  {
    id: 'region-line',
    type: 'line',
    source: 'regions',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': '#3b3b4f',
      'line-width': ['interpolate', ['linear'], ['zoom'], 5.5, 1.4, 8, 2.4, 12, 3.6],
    },
  },
  {
    id: 'county-selected-line',
    type: 'line',
    source: 'counties',
    paint: {
      'line-color': '#111827',
      'line-width': ['case', ['boolean', ['feature-state', 'selected'], false], 3, 0],
    },
  },
  {
    id: 'country-line-halo',
    type: 'line',
    source: 'outline',
    layout: { 'line-join': 'round' },
    paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 5.5, 4, 10, 7], 'line-opacity': 0.8 },
  },
  {
    id: 'country-line',
    type: 'line',
    source: 'outline',
    layout: { 'line-join': 'round' },
    paint: { 'line-color': '#1f2937', 'line-width': ['interpolate', ['linear'], ['zoom'], 5.5, 1.8, 10, 3.2] },
  },
  {
    id: 'commune-label',
    type: 'symbol',
    source: 'labels',
    minzoom: 9,
    filter: ['==', ['get', 'kind'], 'commune'],
    layout: {
      'text-field': ['get', 'name'],
      'text-font': FONT_BOLD,
      'text-size': ['interpolate', ['linear'], ['zoom'], 9, 10, 12, 13],
      'text-transform': 'uppercase',
      'text-letter-spacing': 0.06,
      'text-padding': 6,
      'text-max-width': 7,
    },
    paint: { 'text-color': '#5b3f7a', 'text-halo-color': 'rgba(255,255,255,0.92)', 'text-halo-width': 1.4 },
  },
  {
    id: 'county-label',
    type: 'symbol',
    source: 'labels',
    minzoom: 5.8,
    maxzoom: 10.5,
    filter: ['==', ['get', 'kind'], 'county'],
    layout: {
      'text-field': ['get', 'name'],
      'text-font': FONT_BOLD,
      'text-size': ['interpolate', ['linear'], ['zoom'], 6, 11, 8, 15, 10, 18],
      'text-transform': 'uppercase',
      'text-letter-spacing': 0.08,
      'text-max-width': 8,
      'text-allow-overlap': false,
    },
    paint: {
      'text-color': '#1f2937',
      'text-halo-color': 'rgba(255,255,255,0.9)',
      'text-halo-width': 1.6,
      'text-opacity': ['interpolate', ['linear'], ['zoom'], 9.5, 1, 10.5, 0],
    },
  },
  {
    id: 'region-label',
    type: 'symbol',
    source: 'labels',
    maxzoom: 7,
    filter: ['==', ['get', 'kind'], 'region'],
    layout: {
      'text-field': ['get', 'name'],
      'text-font': FONT_ITALIC,
      'text-size': 15,
      'text-letter-spacing': 0.15,
      'text-offset': [0, 1.6],
    },
    paint: {
      'text-color': '#4b5563',
      'text-halo-color': 'rgba(255,255,255,0.85)',
      'text-halo-width': 1.4,
      'text-opacity': ['interpolate', ['linear'], ['zoom'], 6.2, 0.9, 7, 0],
    },
  },
]

export const FONT_REGULAR = FONT_REG
export type { StyleSpecification }
