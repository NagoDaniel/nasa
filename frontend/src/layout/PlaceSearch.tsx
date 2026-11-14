import { useEffect, useMemo, useRef, useState } from 'react'
import { searchPlaces } from '../api/client'
import type { PlaceResult, Unit } from '../api/types'
import { useI18n } from '../i18n'

const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()

export type Located = { unitId: string | null; lon: number; lat: number; bbox: [number, number, number, number] | null; zoom: number }

/**
 * Search box: commune names from our own data as you type (no network); streets, villages and
 * places from OpenStreetMap on Enter / button (their policy: no search-as-you-type).
 */
export default function PlaceSearch({ units, onLocate }: { units: Unit[]; onLocate: (l: Located) => void }) {
  const { lang } = useI18n()
  const ro = lang === 'ro'
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [places, setPlaces] = useState<PlaceResult[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const box = useRef<HTMLDivElement>(null)

  const local = useMemo(() => {
    const n = norm(q)
    if (n.length < 2) return []
    const byId = new Map(units.map((u) => [u.id, u]))
    return units
      .filter((u) => norm(u.name).includes(n))
      .sort((a, b) => Number(!norm(a.name).startsWith(n)) - Number(!norm(b.name).startsWith(n)) || a.name.localeCompare(b.name, 'ro'))
      .slice(0, 6)
      .map((u) => ({ u, county: u.kind === 'commune' ? byId.get(u.county)?.name : null }))
  }, [q, units])

  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const search = async () => {
    if (q.trim().length < 2) return
    setBusy(true)
    setErr(null)
    setOpen(true)
    try {
      setPlaces((await searchPlaces(q.trim(), lang)).results)
    } catch (e) {
      setErr(String(e))
      setPlaces([])
    } finally {
      setBusy(false)
    }
  }

  const pickUnit = (u: Unit) => {
    onLocate({ unitId: u.id, lon: u.point[0], lat: u.point[1], bbox: null, zoom: u.kind === 'county' ? 8 : 11 })
    setOpen(false)
    setQ(u.name)
  }
  const pickPlace = (p: PlaceResult) => {
    const street = p.type && !['administrative', 'village', 'town', 'city', 'hamlet', 'municipality'].includes(p.type)
    onLocate({ unitId: p.commune?.id ?? null, lon: p.lon, lat: p.lat, bbox: street ? null : p.bbox, zoom: street ? 16 : 13 })
    setOpen(false)
    setQ(p.name)
  }

  const showList = open && (local.length > 0 || places !== null || busy)
  return (
    <div className="place-search" ref={box}>
      <form onSubmit={(e) => { e.preventDefault(); search() }} role="search">
        <input
          type="search" value={q} placeholder={ro ? 'Caută localitate sau stradă…' : 'Search village or street…'}
          onChange={(e) => { setQ(e.target.value); setPlaces(null); setOpen(true) }}
          onFocus={() => setOpen(true)} onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}
          aria-label={ro ? 'Caută un loc' : 'Search a place'}
        />
      </form>
      {showList && (
        <div className="ps-list" role="listbox">
          {local.map(({ u, county }) => (
            <button key={u.id} type="button" className="ps-item" onClick={() => pickUnit(u)}>
              <b>{u.name}</b><span className="muted small">{u.kind === 'county' ? (ro ? 'județ' : 'county') : `${ro ? 'comună' : 'commune'}, ${county}`}</span>
            </button>
          ))}
          {places === null && !busy && q.trim().length >= 2 && (
            <button type="button" className="ps-item ps-more" onClick={search}>
              🔎 {ro ? `Caută străzi și locuri: „${q.trim()}”` : `Search streets & places for “${q.trim()}”`} <span className="muted small">(Enter)</span>
            </button>
          )}
          {busy && <div className="ps-item muted small">…</div>}
          {places?.map((p, i) => (
            <button key={`${p.lon},${p.lat},${i}`} type="button" className="ps-item" onClick={() => pickPlace(p)}>
              <b>{p.name}</b>
              <span className="muted small">{[p.detail, p.commune ? `${ro ? 'com.' : 'commune'} ${p.commune.name}` : (ro ? 'în afara zonei' : 'outside study area')].filter(Boolean).join(' · ')}</span>
            </button>
          ))}
          {places?.length === 0 && !busy && <div className="ps-item muted small">{err ?? (ro ? 'Nimic găsit în zona de studiu.' : 'Nothing found in the study area.')}</div>}
          {places && places.length > 0 && <div className="ps-attr muted">© OpenStreetMap contributors · Nominatim</div>}
        </div>
      )}
    </div>
  )
}
