import { useEffect, useMemo, useRef, useState } from 'react'
import type { FeatureCollection } from 'geojson'
import {
  createField, deleteField, fieldContext, getVegetationJob, listFields, measureField, startVegetation, updateField,
} from '../../api/client'
import type { CellDataset, FieldContextResp, FieldMeasure, SavedField, SoilContext, SmapContext, VegJob, VegObs, VegSource } from '../../api/types'
import Chart, { type ChartOption } from '../../components/Chart'
import Collapsible from '../../components/Collapsible'
import { fmt } from '../../components/format'
import { useI18n } from '../../i18n'
import { fromPolygon, ringAreaHa, toPolygon, type DrawMode } from '../../map/draw'
import { useFieldLink } from '../../state/FieldLink'
import { FIELD_TEXT, type FieldText } from './fieldText'

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
const STATUS_COLOR: Record<string, string> = { clear: '#15803d', partly_cloudy: '#d97706', suspect: '#9333ea', cloudy: '#9ca3af', no_data: '#cbd5e1', error: '#b91c1c' }

type Shown = { img: 'hls' | 's2' | null; cell: { dataset: string; cell: string } | null; soil: boolean; satellite: boolean }

/** "My field": draw / edit / save a field and see data at each dataset's real resolution. */
export default function FieldView({ active }: { active: boolean }) {
  const { lang } = useI18n()
  const F = FIELD_TEXT[lang]
  const fl = useFieldLink()
  const [saved, setSaved] = useState<SavedField[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [measure, setMeasure] = useState<FieldMeasure | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [ctx, setCtx] = useState<FieldContextResp | null>(null)
  const [job, setJob] = useState<VegJob | null>(null)
  const [jobErr, setJobErr] = useState<string | null>(null)
  const [shown, setShown] = useState<Shown>({ img: null, cell: null, soil: false, satellite: false })
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listFields().then(setSaved).catch(() => setSaved([]))
  }, [])

  // Committed outline changed: measure it and load the surrounding-area data.
  useEffect(() => {
    setMeasure(null)
    setCtx(null)
    setErr(null)
    setJob(null)
    setJobErr(null)
    setShown((s) => ({ ...s, img: null, cell: null, soil: false }))
    if (!fl.ring) return
    const c = new AbortController()
    const g = toPolygon(fl.ring)
    const t = window.setTimeout(async () => {
      try {
        const m = await measureField(g, c.signal)
        setMeasure(m)
        setCtx(await fieldContext(g, c.signal))
      } catch (e) {
        if ((e as Error).name !== 'AbortError') setErr((e as Error).message)
      }
    }, 250)
    return () => {
      window.clearTimeout(t)
      c.abort()
    }
  }, [fl.ring])

  // Language switched: fetch the same results again with texts in the new language (no reset).
  const firstLang = useRef(true)
  useEffect(() => {
    if (firstLang.current) {
      firstLang.current = false
      return
    }
    if (!fl.ring) return
    const g = toPolygon(fl.ring)
    measureField(g).then(setMeasure).catch(() => {})
    fieldContext(g).then(setCtx).catch(() => {})
    if (job?.status === 'done') getVegetationJob(job.job_id).then(setJob).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang])

  // Poll the imagery job.
  useEffect(() => {
    if (!job || (job.status !== 'queued' && job.status !== 'running')) return
    const t = window.setTimeout(async () => {
      try {
        setJob(await getVegetationJob(job.job_id))
      } catch (e) {
        setJobErr((e as Error).message)
        setJob(null)
      }
    }, 2000)
    return () => window.clearTimeout(t)
  }, [job])

  // First clear image appears: show it on the map (HLS preferred, the NASA source).
  const veg = job?.result ?? null
  useEffect(() => {
    if (!veg || shown.img) return
    const pick = veg.sources.hls?.latest_clear?.overlay ? 'hls' : veg.sources.s2?.latest_clear?.overlay ? 's2' : null
    if (pick) setShown((s) => ({ ...s, img: pick }))
  }, [veg, shown.img])

  // Map overlays follow what is switched on here.
  const savedFc = useMemo<FeatureCollection>(() => ({
    type: 'FeatureCollection',
    features: saved.filter((f) => f.id !== currentId).map((f) => ({ type: 'Feature', properties: { id: f.id, name: f.name }, geometry: f.geometry })),
  }), [saved, currentId])
  const { setOverlays, fitTo } = fl
  useEffect(() => {
    const src = shown.img ? veg?.sources[shown.img] : null
    const ov = src?.latest_clear?.overlay
    let cells: FeatureCollection | null = null
    if (shown.cell && ctx) {
      const ds = ctx.cells.find((d) => d.dataset === shown.cell!.dataset)
      const c = ds?.cells.find((x) => x.cell === shown.cell!.cell)
      if (ds && c) {
        const v = latestYear(c)
        cells = {
          type: 'FeatureCollection',
          features: [
            { type: 'Feature', properties: {}, geometry: c.geometry },
            { type: 'Feature', properties: { label: `${ds.label}\n${v ? `${fmt(v[1], 1)} ${unitFor(ds)} (${v[0]})` : ''}\n${ds.resolution}` }, geometry: { type: 'Point', coordinates: c.center } },
          ],
        }
      }
    }
    setOverlays({
      image: ov ? { url: ov.image, corners: ov.corners } : null,
      cells,
      soil: shown.soil ? ctx?.soil.pixels?.pixels ?? null : null,
      saved: savedFc,
      satellite: shown.satellite,
    })
  }, [shown, veg, ctx, savedFc, setOverlays])

  const liveHa = fl.liveRing ? ringAreaHa(fl.liveRing) : null
  const setMode = (m: DrawMode) => fl.setMode(fl.mode === m ? (fl.ring ? 'edit' : 'off') : m)

  const loadSaved = (f: SavedField) => {
    setCurrentId(f.id)
    setName(f.name)
    fl.setRing(fromPolygon(f.geometry))
    fl.setMode('edit')
    const xs = f.geometry.coordinates[0].map((p) => p[0])
    const ys = f.geometry.coordinates[0].map((p) => p[1])
    fitTo([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)])
  }
  const save = async () => {
    if (!fl.ring) return
    setBusy(true)
    try {
      const g = toPolygon(fl.ring)
      const f = currentId ? await updateField(currentId, { name, geometry: g }) : await createField(name, g)
      setCurrentId(f.id)
      setName(f.name)
      setSaved(await listFields())
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const remove = async (id: number) => {
    if (!window.confirm(F.confirmDelete)) return
    try {
      await deleteField(id)
      if (id === currentId) setCurrentId(null)
      setSaved(await listFields())
    } catch (e) {
      setErr((e as Error).message)
    }
  }
  const clear = () => {
    fl.setRing(null)
    fl.setMode('off')
    setCurrentId(null)
    setName('')
  }
  const loadVeg = async () => {
    if (!fl.ring) return
    setJobErr(null)
    try {
      setJob(await startVegetation(toPolygon(fl.ring)))
    } catch (e) {
      setJobErr((e as Error).message)
    }
  }

  if (!active && !fl.ring) return null

  return (
    <div className="view field-view">
      <div className="block stack">
        <div className="chips">
          {(['rect', 'poly'] as const).map((m) => (
            <button key={m} type="button" className={`chip ${fl.mode === m ? 'on' : ''}`} onClick={() => setMode(m)}>
              {m === 'rect' ? '▭ ' : '⬠ '}{F[m]}
            </button>
          ))}
          <button type="button" className={`chip ${fl.mode === 'edit' ? 'on' : ''}`} disabled={!fl.ring} onClick={() => setMode('edit')}>✎ {F.edit}</button>
          <button type="button" className={`chip ${shown.satellite ? 'on' : ''}`} onClick={() => setShown((s) => ({ ...s, satellite: !s.satellite }))}>{F.satellite}</button>
          {fl.ring && <button type="button" className="link" onClick={clear}>{F.clear}</button>}
        </div>
        <p className="hint">{F[`hint_${fl.mode}` as keyof FieldText] as string}</p>

        {!fl.ring && liveHa === null && <p className="muted">{F.noField}</p>}
        {(fl.ring || liveHa !== null) && (
          <div className="field-summary">
            <div>
              <span className="muted small">{F.area}</span>
              <div className="field-area">{fmt(measure?.area_ha ?? liveHa ?? 0, (measure?.area_ha ?? liveHa ?? 0) < 10 ? 2 : 1)} ha</div>
            </div>
            {measure && (
              <div className="small">
                {F.perimeter} {fmt(measure.perimeter_m, 0)} m ·{' '}
                {measure.commune ? <>{F.inCommune} <b>{measure.commune.name}</b> ({measure.commune.county_name})</> : F.outsideAoi}
              </div>
            )}
          </div>
        )}
        {measure?.warnings?.map((w) => <p key={w} className="note warn small">{w}</p>)}
        {err && <p className="note warn small">{err}</p>}

        {fl.ring && measure && (
          <div className="field-save">
            <input type="text" maxLength={60} value={name} placeholder={F.name} aria-label={F.name} onChange={(e) => setName(e.target.value)} />
            <button type="button" onClick={save} disabled={busy}>{currentId ? F.saveChanges : F.save}</button>
          </div>
        )}
        <details className="field-saved" open={saved.length > 0 && !fl.ring}>
          <summary>{F.saved} ({saved.length})</summary>
          {saved.length === 0 && <p className="muted small">{F.noSaved}</p>}
          <ul>
            {saved.map((f) => (
              <li key={f.id} className={f.id === currentId ? 'on' : ''}>
                <button type="button" className="link" onClick={() => loadSaved(f)}>{f.name}</button>
                <span className="muted small">{f.area_ha !== null ? `${fmt(f.area_ha, f.area_ha < 10 ? 2 : 1)} ha` : ''}</span>
                <button type="button" className="link danger small" onClick={() => remove(f.id)}>{F.del}</button>
              </li>
            ))}
          </ul>
        </details>
      </div>

      {fl.ring && measure && (
        <>
          <Vegetation F={F} job={job} jobErr={jobErr} onLoad={loadVeg} shown={shown.img}
            setShown={(img) => setShown((s) => ({ ...s, img }))} />
          {!ctx && !err && <p className="muted pad">{F.loadingCtx}</p>}
          {ctx && (
            <Coarse F={F} ctx={ctx} shown={shown} setShown={setShown} onFit={fitTo} fieldBbox={measure.bbox} />
          )}
        </>
      )}
    </div>
  )
}

// ----------------------------------------------------------------------------- vegetation
function vegSummary(F: FieldText, job: VegJob | null): string {
  if (!job) return F.notLoaded
  if (job.status === 'queued' || job.status === 'running') {
    const p = job.progress.total ? Math.round((100 * job.progress.done) / job.progress.total) : 0
    return F.loadingPct.replace('{p}', String(p))
  }
  if (job.status === 'error') return F.st_error
  const parts = (['hls', 's2'] as const).flatMap((k) => {
    const lc = job.result?.sources[k]?.latest_clear
    return lc?.ndvi ? [`${k === 'hls' ? 'HLS' : 'S2'} ${fmt(lc.ndvi.median, 2)}`] : []
  })
  return parts.length ? `NDVI ${parts.join(' · ')}` : F.none
}

function Vegetation({ F, job, jobErr, onLoad, shown, setShown }: {
  F: FieldText
  job: VegJob | null
  jobErr: string | null
  onLoad: () => void
  shown: 'hls' | 's2' | null
  setShown: (s: 'hls' | 's2' | null) => void
}) {
  const r = job?.result
  const running = job && (job.status === 'queued' || job.status === 'running')
  return (
    <Collapsible id="field-veg" title={F.measuredTitle} summary={vegSummary(F, job)}
      info={<>{F.measuredSub} {F.ndviInfo}</>}>
      <p className="muted small"><span className="badge kind-measured">{F.measured}</span> {F.measuredSub}</p>
      {!job && (
        <div className="stack">
          <button type="button" className="primary" onClick={onLoad}>{F.loadVeg}</button>
          <p className="muted small">{F.loadVegNote}</p>
        </div>
      )}
      {jobErr && <p className="note warn small">{jobErr}</p>}
      {job?.status === 'error' && (
        <p className="note warn small">{job.error} <button type="button" className="link" onClick={onLoad}>{F.retry}</button></p>
      )}
      {running && (
        <div className="field-progress">
          <div className="small">{job.stage === 'reading pixels' ? F.reading : job.stage === 'searching catalogues' ? F.searching : job.stage === 'queued' ? F.queued : job.stage} · {job.progress.done}/{job.progress.total || '…'}</div>
          <div className="bar"><i style={{ width: `${job.progress.total ? (100 * job.progress.done) / job.progress.total : 5}%` }} /></div>
        </div>
      )}
      {r && (
        <>
          <p className="muted tiny">{r.index}. {F.fetched}: {r.fetched_at.replace('T', ' ')} UTC · {r.season.start} – {r.season.end}</p>
          {(['hls', 's2'] as const).map((k) => r.sources[k] ? (
            <SourceBlock key={k} F={F} k={k} s={r.sources[k]!} pending={r.pending.includes(k)} shown={shown === k}
              toggle={() => setShown(shown === k ? null : k)} rules={r.status_rules} />
          ) : r.pending.includes(k) ? <p key={k} className="muted small">{k.toUpperCase()}: {F.pendingSource}</p> : null)}
        </>
      )}
    </Collapsible>
  )
}

function SourceBlock({ F, k, s, pending, shown, toggle, rules }: {
  F: FieldText
  k: 'hls' | 's2'
  s: VegSource
  pending: boolean
  shown: boolean
  toggle: () => void
  rules: Record<string, string>
}) {
  const name = s.short ?? (k === 'hls' ? 'HLS' : 'Sentinel-2')
  const title = <>{name} · {s.resolution_m ?? (k === 'hls' ? 30 : 10)} m {s.status === 'ok' && !s.nasa && <span className="badge">{F.notNasa}</span>}</>
  if (s.status !== 'ok') {
    return (
      <Collapsible id={`field-src-${k}`} title={title} summary={F.st_error}>
        <p className="note warn small">{s.note}</p>
      </Collapsible>
    )
  }
  const obs = s.observations ?? []
  const lc = s.latest_clear
  const c = s.counts ?? {}
  const peaks = s.peaks ?? []
  return (
    <Collapsible id={`field-src-${k}`} title={title} info={<>{s.label}. {s.cloud_mask}.</>}
      summary={pending ? F.pendingSource : lc?.ndvi ? `NDVI ${fmt(lc.ndvi.median, 2)} · ${lc.date}` : F.none}>
      <p className="muted tiny">{s.label} · {s.cloud_mask}</p>
      {lc ? (
        <div className="field-latest">
          <div>
            <span className="muted small">{F.latestClear} · {lc.date} · {lc.sensor}</span>
            <div className="field-ndvi">NDVI {fmt(lc.ndvi!.median, 2)} <span className="muted small">({fmt(lc.ndvi!.p10, 2)}–{fmt(lc.ndvi!.p90, 2)})</span></div>
            <span className="muted small">{lc.pixels_in_field} {F.pixelsInField} · {lc.pixel_size_m} m · {fmt(lc.valid_pct ?? 0, 0)}% {F.clearPx}</span>
          </div>
          {lc.overlay && <button type="button" className={`chip ${shown ? 'on' : ''}`} onClick={toggle}>{shown ? F.hideFromMap : F.showOnMap}</button>}
        </div>
      ) : <p className="muted small">{F.none}</p>}
      <div className="field-counts small">
        <span className="muted">{F.counts}:</span>
        <Count n={c.clear} label={F.clearN} st="clear" info={rules.clear} />
        <Count n={c.partly_cloudy} label={F.partlyN} st="partly_cloudy" info={rules.partly_cloudy} />
        <Count n={c.suspect} label={F.suspectN} st="suspect" info={rules.suspect} />
        <Count n={c.cloudy} label={F.cloudyN} st="cloudy" info={rules.cloudy} />
        <Count n={c.no_data} label={F.nodataN} st="no_data" info={rules.no_data} />
        <Count n={c.error} label={F.errorN} st="error" info={rules.error} />
      </div>
      {obs.length > 0 && (
        <Collapsible id={`field-src-${k}-chart`} title={F.seasonChart} summary={`${obs.length} ${F.imagesN}`}>
          <SeasonChart F={F} obs={obs} />
        </Collapsible>
      )}
      {peaks.length > 0 && (
        <Collapsible id={`field-src-${k}-peaks`} title={F.peaks} info={F.peaksNote}
          summary={`${peaks[0].year}–${peaks[peaks.length - 1].year}`}>
          <table className="field-table small">
            <tbody>
              {peaks.map((p) => (
                <tr key={p.year}>
                  <td>{p.year}</td>
                  <td>{p.value !== null ? <b>{fmt(p.value, 2)}</b> : <span className="muted">{p.status === 'cloudy' ? F.st_cloudy : F.st_no_data}</span>}</td>
                  <td className="muted">n = {p.n_used}/{p.n_read}{p.dates.length ? ` · ${p.dates.join(', ')}` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Collapsible>
      )}
      <Collapsible id={`field-src-${k}-obs`} title={F.observations} summary={`${obs.length}`}>
        <div className="field-table-wrap">
          <table className="field-table tiny">
            <thead><tr><th>{F.date}</th><th>{F.sensor}</th><th>{F.status}</th><th>NDVI</th><th>{F.clearPx}</th><th>{F.sceneCloud}</th></tr></thead>
            <tbody>
              {[...obs].reverse().map((o) => (
                <tr key={o.item_id}>
                  <td className="nowrap">{o.date}</td>
                  <td>{o.sensor}</td>
                  <td><span className="dot" style={{ background: STATUS_COLOR[o.status] }} /> {F[`st_${o.status}` as keyof FieldText] as string}</td>
                  <td>{o.ndvi ? fmt(o.ndvi.median, 2) : '–'}</td>
                  <td title={o.note}>{o.valid_pct !== null ? `${fmt(o.valid_pct, 0)}% (${o.valid_pixels}/${o.pixels_in_field})` : (o.note ?? '–')}</td>
                  <td>{o.scene_cloud_pct !== null ? `${fmt(o.scene_cloud_pct, 0)}%` : '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Collapsible>
    </Collapsible>
  )
}

function Count({ n, label, st, info }: { n?: number; label: string; st: string; info: string }) {
  if (!n) return null
  return <span className="nowrap" title={info}><span className="dot" style={{ background: STATUS_COLOR[st] }} /> {n} {label}</span>
}

function SeasonChart({ F, obs }: { F: FieldText; obs: VegObs[] }) {
  const option = useMemo<ChartOption>(() => {
    const pt = (o: VegObs, y: number) => ({ value: [o.date, y], o })
    const clear = obs.filter((o) => o.status === 'clear' && o.ndvi).map((o) => pt(o, o.ndvi!.median))
    const partly = obs.filter((o) => o.status === 'partly_cloudy' && o.ndvi).map((o) => pt(o, o.ndvi!.median))
    const suspect = obs.filter((o) => o.status === 'suspect' && o.ndvi).map((o) => pt(o, o.ndvi!.median))
    const none = obs.filter((o) => !o.ndvi).map((o) => pt(o, -0.12))
    const label = (o: VegObs) => F[`st_${o.status}` as keyof FieldText] as string
    return {
      grid: { left: 38, right: 12, top: 18, bottom: 26 },
      xAxis: { type: 'time', axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', min: -0.2, max: 1, interval: 0.2, name: 'NDVI', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10, formatter: (v: number) => (v < 0 ? '' : v.toFixed(1)) } },
      tooltip: {
        trigger: 'item',
        formatter: (p: { data: { o: VegObs } }) => {
          const o = p.data.o
          return `<b>${esc(o.date)}</b> · ${esc(o.sensor)}<br>${esc(label(o))}${o.ndvi ? ` · NDVI ${o.ndvi.median.toFixed(2)} (${o.ndvi.p10.toFixed(2)}–${o.ndvi.p90.toFixed(2)})` : ''}` +
            `<br>${o.valid_pct !== null ? `${o.valid_pct.toFixed(0)}% ${esc(F.clearPx)} · ` : ''}${o.pixel_size_m} m` +
            (o.status === 'suspect' && o.note ? `<br><i>${esc(o.note)}</i>` : '')
        },
      },
      series: [
        { type: 'line', name: F.st_clear, data: clear, symbolSize: 6, itemStyle: { color: STATUS_COLOR.clear }, lineStyle: { width: 1.5 } },
        { type: 'line', name: F.st_partly_cloudy, data: partly, symbol: 'emptyCircle', symbolSize: 7, itemStyle: { color: STATUS_COLOR.partly_cloudy }, lineStyle: { opacity: 0 } },
        { type: 'line', name: F.st_suspect, data: suspect, symbol: 'emptyDiamond', symbolSize: 9, itemStyle: { color: STATUS_COLOR.suspect }, lineStyle: { opacity: 0 } },
        { type: 'line', name: F.st_cloudy, data: none, symbol: 'triangle', symbolSize: 6, itemStyle: { color: STATUS_COLOR.cloudy }, lineStyle: { opacity: 0 } },
      ],
    }
  }, [obs, F])
  return <Chart option={option} height={170} />
}

// ----------------------------------------------------------------------------- coarse data
function latestYear(c: { yearly?: Record<string, number> }): [string, number] | null {
  const ys = Object.keys(c.yearly ?? {}).sort()
  const y = ys[ys.length - 1]
  return y ? [y, c.yearly![y]] : null
}
const unitFor = (d: CellDataset) => (d.aggregation === 'sum' ? `${d.unit}/yr` : d.unit)

function cellSummary(F: FieldText, d: CellDataset): string {
  const ok = d.cells.filter((c) => c.status === 'ok')
  if (!ok.length) return '–'
  if (d.cells.length > 1) return `${d.cells.length} ${F.cellsN}`
  const ly = latestYear(ok[0])
  return ly ? `${fmt(ly[1], 1)} ${unitFor(d)} (${ly[0]})` : '–'
}

function Coarse({ F, ctx, shown, setShown, onFit, fieldBbox }: {
  F: FieldText
  ctx: FieldContextResp
  shown: Shown
  setShown: (f: (s: Shown) => Shown) => void
  onFit: (b: [number, number, number, number], z?: number) => void
  fieldBbox: [number, number, number, number]
}) {
  const toggleCell = (dataset: string, cell: string, geom: number[][][]) => {
    const on = shown.cell?.dataset === dataset && shown.cell.cell === cell
    setShown((s) => ({ ...s, cell: on ? null : { dataset, cell } }))
    if (on) onFit(fieldBbox)
    else {
      const xs = geom[0].map((p) => p[0])
      const ys = geom[0].map((p) => p[1])
      onFit([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], 13)
    }
  }
  return (
    <>
      <Collapsible id="field-coarse" title={F.coarseTitle} info={F.coarseSub} summary={F.datasetsN.replace('{n}', String(ctx.cells.length))}>
        <p className="note small field-estimate-note"><span className="badge kind-estimate">{F.estimate}</span> {F.coarseSub}</p>
        {ctx.cells.map((d) => (
          <Collapsible key={d.dataset} id={`field-cell-${d.dataset}`} title={d.label} summary={cellSummary(F, d)}>
            <p className="muted tiny">{d.resolution}. {d.about} {F.source}: {d.source}. {F.period}: {d.period.start} – {d.period.end}.</p>
            {d.cells.length > 1 && <p className="small">{F.spansCells.replace('{n}', String(d.cells.length))}</p>}
            {d.cells.map((c) => {
              const ly = latestYear(c)
              const on = shown.cell?.dataset === d.dataset && shown.cell.cell === c.cell
              return (
                <div key={c.cell} className="field-cell-row">
                  <div>
                    {c.status === 'no_data' ? <span className="muted">{F.st_no_data}</span> : (
                      <>
                        <div>{F.latestYear}: <b>{ly ? `${fmt(ly[1], 1)} ${unitFor(d)}` : '–'}</b>{ly && <span className="muted"> ({ly[0]})</span>}</div>
                        {c.latest_month && <div className="small">{F.latestMonth}: {fmt(c.latest_month.value, 1)} {d.unit} <span className="muted">({c.latest_month.month})</span></div>}
                      </>
                    )}
                    <div className="muted tiny">
                      {F.cellOf} ≈ {fmt(c.cell_area_km2, 0)} km² · {F.fieldIsOfCell.replace('{p}', c.field_share_of_cell_pct !== null ? fmt(c.field_share_of_cell_pct, c.field_share_of_cell_pct < 0.01 ? 4 : 2) : '–')}
                      {d.cells.length > 1 && ` · ${F.ofField.replace('{p}', fmt(c.share_of_field_pct, 0))}`}
                      {!!c.missing_months && ` · ${c.missing_months} ${F.missing}`}
                    </div>
                  </div>
                  <button type="button" className={`chip ${on ? 'on' : ''}`} onClick={() => toggleCell(d.dataset, c.cell, c.geometry.coordinates)}>
                    {on ? F.hideCell : F.showCell}
                  </button>
                </div>
              )
            })}
          </Collapsible>
        ))}
        {shown.cell && <button type="button" className="link" onClick={() => { setShown((s) => ({ ...s, cell: null })); onFit(fieldBbox) }}>← {F.backToField}</button>}
      </Collapsible>
      <SoilBlock F={F} soil={ctx.soil} shown={shown.soil} toggle={() => setShown((s) => ({ ...s, soil: !s.soil }))} />
      {ctx.smap && <SmapBlock F={F} smap={ctx.smap} />}
    </>
  )
}

function SoilBlock({ F, soil, shown, toggle }: { F: FieldText; soil: SoilContext; shown: boolean; toggle: () => void }) {
  const px = soil.pixels
  const v = soil.values ?? {}
  const summary = soil.status !== 'ok' ? F.st_no_data
    : [v.phh2o && `pH ${fmt(v.phh2o.mean, 1)}`, v.soc && `SOC ${fmt(v.soc.mean, 1)} g/kg`].filter(Boolean).join(' · ')
  return (
    <Collapsible id="field-soil" title={F.soilTitle} info={soil.note} summary={summary}>
      <p className="muted small"><span className="badge kind-model">{F.model}</span> {soil.note}</p>
      {px && (
        <div className="field-latest">
          <span className="small">{F.soilPixels.replace('{n}', String(px.count)).replace('{a}', fmt(px.pixel_area_ha, 1))} ({px.pixel_size_m[0]} × {px.pixel_size_m[1]} m) · {px.selection}</span>
          <button type="button" className={`chip ${shown ? 'on' : ''}`} onClick={toggle}>{shown ? F.hidePixels : F.showPixels}</button>
        </div>
      )}
      {soil.status === 'ok' && soil.values && (
        <table className="field-table small">
          <tbody>
            {Object.entries(soil.values).map(([k, val]) => (
              <tr key={k}>
                <td>{soil.properties[k]?.label}</td>
                <td><b>{val ? fmt(val.mean, 1) : '–'}</b> {soil.properties[k]?.unit === 'pH' ? '' : soil.properties[k]?.unit}</td>
                <td className="muted">{val && val.min !== val.max ? `${fmt(val.min, 1)}–${fmt(val.max, 1)}` : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted tiny">{F.source}: {soil.source}. {F.resolution}: {soil.resolution ?? '250 m'}.</p>
    </Collapsible>
  )
}

function SmapBlock({ F, smap }: { F: FieldText; smap: SmapContext }) {
  const lm = smap.status === 'ok' ? smap.latest_month : null
  return (
    <Collapsible id="field-smap" title={F.smapTitle} info={smap.note}
      summary={lm ? `${fmt(lm.value, 3)} ${smap.unit} (${lm.month})` : F.st_no_data}>
      <p className="muted small"><span className="badge kind-estimate">{F.communeAvg}</span> {smap.note}</p>
      {lm && <div>{F.latestMonth}: <b>{fmt(lm.value, 3)} {smap.unit}</b> <span className="muted">({lm.month})</span></div>}
      <p className="muted tiny">{F.source}: {smap.source}. {F.resolution}: {smap.resolution}.</p>
    </Collapsible>
  )
}
