import type { FeatureCollection } from 'geojson'

const BASE = '/api'

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`)
  return res.json() as Promise<T>
}

export type GeoLayer = 'counties' | 'regions' | 'communes' | 'outline' | 'mask' | 'labels'

export const getGeoLayer = (layer: GeoLayer) => getJson<FeatureCollection>(`/geo/${layer}`)
