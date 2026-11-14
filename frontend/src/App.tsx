import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getMapLayer, getUnits } from './api/client'
import type { MapLayerData } from './api/types'
import { useAsync } from './components/useAsync'
import { I18nProvider, useI18n } from './i18n'
import type { Dict } from './i18n/en'
import AssistantWidget from './assistant/AssistantWidget'
import AreaBar from './layout/AreaBar'
import MapLegend from './layout/MapLegend'
import Sidebar from './layout/Sidebar'
import RomaniaMap, { type MapHandle, type MapPick } from './map/RomaniaMap'
import { makeScale } from './map/scales'
import { MapLink, sameSpec, type AppCommand, type LayerSpec, type MapLinkCtx, type ResolvedLayer } from './state/MapLink'
import { SECTIONS, type FarmerSection, type ProcurementSection, type Role, type Section } from './state/sections'
import FarmerView from './views/farmer/FarmerView'
import ProcurementView from './views/procurement/ProcurementView'

const AOI_BOUNDS: [[number, number], [number, number]] = [[20.6, 44.4], [25.4, 47.7]]

function usePersisted(key: string, initial: boolean): [boolean, (v: boolean) => void] {
  const [v, setV] = useState(() => {
    try {
      const s = localStorage.getItem(key)
      return s === null ? initial : s === '1'
    } catch {
      return initial
    }
  })
  const set = useCallback((n: boolean) => {
    setV(n)
    try {
      localStorage.setItem(key, n ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  }, [key])
  return [v, set]
}

function Shell() {
  const { t } = useI18n()
  const [role, setRole] = useState<Role>('farmer')
  const [sections, setSections] = useState<{ farmer: FarmerSection; procurement: ProcurementSection }>({ farmer: 'overview', procurement: 'sourcing' })
  const section = sections[role]
  const [navCollapsed, setNavCollapsed] = usePersisted('s2f.nav.collapsed', false)
  const [panelOpen, setPanelOpen] = usePersisted('s2f.panel.open', true)

  const [selectedId, setSelectedId] = useState('AB')
  const [notice, setNotice] = useState<string | null>(null)
  const units = useAsync('units', getUnits)
  const byId = useMemo(() => new Map((units.data ?? []).map((u) => [u.id, u])), [units.data])
  const sel = byId.get(selectedId)
  const countyCode = selectedId.split('-')[0]
  const countyName = byId.get(countyCode)?.name ?? countyCode
  const mapRef = useRef<MapHandle>(null)

  // What the map is coloured by.
  const [spec, setSpecState] = useState<LayerSpec | null>(null)
  const [year, setYear] = useState<string | null>(null)
  const [custom, setCustomLayer] = useState<ResolvedLayer | null>(null)
  const [highlight, setHighlight] = useState<string | null>(null)
  const [hoveredOnMap, setHoveredOnMap] = useState<string | null>(null)
  const layerKey = spec ? `${spec.kind}:${spec.key}` : null
  const fetched = useAsync(layerKey, () => getMapLayer(spec!.kind, spec!.key))
  const data: MapLayerData | null = fetched.data && spec && fetched.data.kind === spec.kind && fetched.data.key === spec.key ? fetched.data : null

  const setSpec = useCallback((s: LayerSpec | null, y?: string) => {
    setSpecState((prev) => (sameSpec(prev, s) || (!prev && !s) ? prev : s))
    if (y) setYear(y)
  }, [])

  // Assistant commands. A requested year waits until that layer's data has arrived.
  const [command, setCommand] = useState<AppCommand | null>(null)
  const cmdSeq = useRef(0)
  const pendingYear = useRef<{ kind: string; key: string; year: string } | null>(null)
  const runCommand = useCallback<MapLinkCtx['runCommand']>((c) => {
    if (c.type === 'layer' && c.year) pendingYear.current = { kind: c.spec.kind, key: c.spec.key, year: c.year }
    setCommand({ ...c, seq: ++cmdSeq.current })
  }, [])

  // Keep the year valid for the current layer (default: the latest year).
  useEffect(() => {
    if (!data?.years) return
    const p = pendingYear.current
    if (p && p.kind === data.kind && p.key === data.key) {
      pendingYear.current = null
      if (data.years.includes(p.year)) return setYear(p.year)
    }
    if (!year || !data.years.includes(year)) setYear(data.years[data.years.length - 1])
  }, [data, year])

  const scale = useMemo(
    () => (data ? makeScale(Object.values(data.values).flat().filter((v): v is number => v !== null), data.palette) : null),
    [data],
  )
  const farmerLayer = useMemo<ResolvedLayer | null>(() => {
    if (!data || !scale) return null
    const i = data.years ? data.years.indexOf(year ?? '') : 0
    if (i < 0) return null
    return {
      label: data.label,
      unit: data.unit,
      values: Object.fromEntries(Object.entries(data.values).map(([id, arr]) => [id, arr[i] ?? null])),
      scale,
      level: 'commune',
      source: data.source,
    }
  }, [data, scale, year])
  const layer = role === 'procurement' ? custom : farmerLayer

  const selectArea = useCallback((id: string) => {
    const u = byId.get(id)
    if (!u) return
    setSelectedId(id)
    setNotice(null)
    mapRef.current?.flyTo(u.point, u.kind === 'county' ? 7.7 : 10.2)
  }, [byId])

  const onMapSelect = useCallback((p: MapPick) => {
    if (!p.inAoi) return setNotice(p.name)
    setNotice(null)
    setSelectedId(p.id)
  }, [])

  const goTo = useCallback((s: string) => {
    const r: Role = (SECTIONS.farmer as readonly string[]).includes(s) ? 'farmer' : 'procurement'
    setRole(r)
    setSections((prev) => ({ ...prev, [r]: s }))
  }, [])

  const link = useMemo<MapLinkCtx>(
    () => ({ spec, setSpec, year, setYear, years: data?.years ?? null, setCustomLayer, setHighlight, hoveredOnMap, selectArea, goTo, command, runCommand }),
    [spec, setSpec, year, data, hoveredOnMap, selectArea, goTo, command, runCommand],
  )

  return (
    <MapLink.Provider value={link}>
      <div className={`app ${navCollapsed ? 'nav-collapsed' : ''} ${panelOpen ? '' : 'panel-closed'}`}>
        <Sidebar
          role={role} setRole={setRole}
          section={section} setSection={(s: Section) => goTo(s)}
          collapsed={navCollapsed} setCollapsed={setNavCollapsed}
        />
        <div className="main">
          <AreaBar units={units.data ?? []} selectedId={selectedId} onSelect={selectArea} notice={notice} />
          <div className="work">
            <div className="map-pane">
              <RomaniaMap
                ref={mapRef}
                selectedId={selectedId}
                onSelect={onMapSelect}
                highlightId={highlight}
                onHover={setHoveredOnMap}
                layer={layer}
                initialBounds={AOI_BOUNDS}
                outsideLabel={t('outsideStudy')}
                noDataLabel={t('noData')}
                countyFigureLabel={t('countyFigure')}
              />
              <MapLegend
                layer={layer}
                years={role === 'farmer' ? data?.years ?? null : null}
                year={year}
                setYear={setYear}
                loading={role === 'farmer' && !!spec && !data}
              />
              <AssistantWidget byId={byId} selectedId={selectedId} role={role} section={section} />
              {!panelOpen && (
                <button type="button" className="panel-open-btn" onClick={() => setPanelOpen(true)}>‹ {t('showPanel')}</button>
              )}
            </div>
            <section className="panel" aria-label={t(`nav_${section}` as keyof Dict)}>
              <header className="panel-head">
                <div>
                  <div className="panel-area">{sel?.name ?? 'Alba'}{sel?.kind === 'commune' && <span className="muted"> · {countyName}</span>}</div>
                  <h2>{t(`nav_${section}` as keyof Dict)}</h2>
                  <p className="muted">{t(`intro_${section}` as keyof Dict)}</p>
                </div>
                <button type="button" className="icon-btn" onClick={() => setPanelOpen(false)} title={t('hidePanel')} aria-label={t('hidePanel')}>
                  <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
              </header>
              <div className="panel-body">
                <div hidden={role !== 'farmer'}>
                  <FarmerView unitId={selectedId} countyName={countyName} section={sections.farmer} active={role === 'farmer'} />
                </div>
                <div hidden={role !== 'procurement'}>
                  <ProcurementView section={sections.procurement} selectedCounty={countyCode} active={role === 'procurement'} />
                </div>
                <footer className="foot">
                  {t('notEndorsed')} Data: NASA POWER, GPM IMERG, GLDAS, FIRMS, MODIS · ISRIC SoilGrids · JRC EUCROPMAP · INS TEMPO · geoBoundaries · © OpenStreetMap contributors.
                </footer>
              </div>
            </section>
          </div>
        </div>
      </div>
    </MapLink.Provider>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <Shell />
    </I18nProvider>
  )
}
