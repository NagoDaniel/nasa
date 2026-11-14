import type { FeatureCollection } from 'geojson'
import type { AreaBundle, Forecast, MapLayerData, Priorities, ProcurementResponse, ScoreResponse, Unit } from './types'

const BASE = '/api'

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* not json */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

export type GeoLayer = 'counties' | 'regions' | 'communes' | 'outline' | 'mask' | 'labels'

export const getGeoLayer = (layer: GeoLayer) => getJson<FeatureCollection>(`/geo/${layer}`)
export const getUnits = () => getJson<Unit[]>('/units')
export const getArea = (id: string) => getJson<AreaBundle>(`/area/${encodeURIComponent(id)}`)
export const getMapLayer = (kind: string, key: string) =>
  getJson<MapLayerData>(`/map?kind=${encodeURIComponent(kind)}&key=${encodeURIComponent(key)}`)
export const getForecast = (crop: string) => getJson<Forecast>(`/forecast?crop=${encodeURIComponent(crop)}`)
export const getProcurement = (crop: string) => getJson<ProcurementResponse>(`/procurement?crop=${encodeURIComponent(crop)}`)

export const scoreRotations = (unit: string, priorities: Priorities, rotations: { name: string; crops: string[] }[], signal?: AbortSignal) =>
  getJson<ScoreResponse>('/rotations/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ unit, priorities, rotations }),
    signal,
  })
