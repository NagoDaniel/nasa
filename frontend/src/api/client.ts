import type { FeatureCollection } from 'geojson'
import type { AreaBundle, AssistantStatus, ChatContext, ChatResponse, ChatTurn, MapLayerData, Priorities, ProcurementResponse, ScoreResponse, Unit } from './types'

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
export const getProcurement = (crop: string) => getJson<ProcurementResponse>(`/procurement?crop=${encodeURIComponent(crop)}`)

export const scoreRotations = (unit: string, priorities: Priorities, rotations: { name: string; crops: string[] }[], signal?: AbortSignal) =>
  getJson<ScoreResponse>('/rotations/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ unit, priorities, rotations }),
    signal,
  })

export const getAssistantStatus = () => getJson<AssistantStatus>('/assistant/status')

/** Chat with the assistant. 429 / 503 still carry a normal reply (with retryAfter in seconds). */
export async function postChat(message: string, history: ChatTurn[], context: ChatContext, signal?: AbortSignal): Promise<ChatResponse & { retryAfter?: number }> {
  const res = await fetch(`${BASE}/assistant/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, context }),
    signal,
  })
  if (res.ok || res.status === 429 || res.status === 503) {
    const body = (await res.json()) as ChatResponse
    const ra = Number(res.headers.get('Retry-After'))
    return res.ok ? body : { ...body, retryAfter: Number.isFinite(ra) && ra > 0 ? ra : 30 }
  }
  throw new Error(String(res.status))
}
