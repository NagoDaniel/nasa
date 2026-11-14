import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getPlannerField, listFields, makePlan } from '../../api/client'
import type { PlanAnswers, PlanCrop, PlannerField, PlanResponse, SavedField } from '../../api/types'
import { fmt } from '../../components/format'
import { useI18n } from '../../i18n'
import { cropName } from '../../i18n/names'
import { fromPolygon } from '../../map/draw'
import { useFieldLink } from '../../state/FieldLink'
import PrioritiesPanel from '../farmer/PrioritiesPanel'
import PlanResult from './PlanResult'
import { PROBLEMS, usePlanText } from './text'

export const PLAN_CROPS: PlanCrop[] = ['maize', 'wheat', 'barley', 'oats', 'pea', 'chickpea', 'sunflower', 'soy', 'flax']
const ROW: PlanCrop[] = ['maize', 'sunflower', 'soy']

function defaults(start: number): PlanAnswers {
  return {
    history: [], consider: [...PLAN_CROPS], avoid: [], must_grow: null, must_min: 1, irrigation: 'no', planter: true, combine: true,
    n_limit: null, contract_crop: null, priorities: { yield: 25, water: 25, soil: 25, risk: 25 }, risk: 'balanced', maturity: {},
    prices: {}, costs: {}, soil_test: { ph: null, soc_g_kg: null, texture: null }, problems: [], years: 4,
    ...(start ? {} : {}),
  }
}

/* ---------- small inputs ---------- */
function Seg<V extends string | number>({ value, options, onChange }: { value: V; options: [V, ReactNode][]; onChange: (v: V) => void }) {
  return (
    <div className="seg big">
      {options.map(([v, label]) => <button key={String(v)} type="button" className={v === value ? 'on' : ''} onClick={() => onChange(v)}>{label}</button>)}
    </div>
  )
}

function CropChips({ value, onChange, only }: { value: PlanCrop[]; onChange: (v: PlanCrop[]) => void; only?: PlanCrop[] }) {
  const { lang } = useI18n()
  return (
    <div className="chips">
      {(only ?? PLAN_CROPS).map((c) => (
        <button key={c} type="button" className={`chip ${value.includes(c) ? 'on' : ''}`}
          onClick={() => onChange(value.includes(c) ? value.filter((x) => x !== c) : [...value, c])}>
          {cropName(c, lang)}
        </button>
      ))}
    </div>
  )
}

function CropSelect({ value, onChange, none }: { value: PlanCrop | null; onChange: (v: PlanCrop | null) => void; none: string }) {
  const { lang } = useI18n()
  return (
    <select value={value ?? ''} onChange={(e) => onChange((e.target.value || null) as PlanCrop | null)}>
      <option value="">{none}</option>
      {PLAN_CROPS.map((c) => <option key={c} value={c}>{cropName(c, lang)}</option>)}
    </select>
  )
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  )
}

/** One question: title, input, and the reason we ask. Top-level so inputs keep focus while typing. */
function QCard({ q, why, optional, children }: { q: string; why: string; optional: boolean; children: ReactNode }) {
  const { T } = usePlanText()
  return (
    <div className="wiz-card">
      <h3>{q}{optional && <span className="muted small"> · {T.optional}</span>}</h3>
      {children}
      <p className="wiz-why"><b>{T.whyAsk}:</b> {why}</p>
    </div>
  )
}

const num = (s: string): number | null => (s.trim() === '' || Number.isNaN(Number(s)) ? null : Number(s))

/* ---------- the view ---------- */
export default function PlanView({ active, goDraw }: { active: boolean; goDraw: () => void }) {
  const { T, problem, lang } = usePlanText()
  const fl = useFieldLink()
  const [fields, setFields] = useState<SavedField[] | null>(null)
  const [fieldId, setFieldId] = useState<number | null>(null)
  const [info, setInfo] = useState<PlannerField | null>(null)
  const [a, setA] = useState<PlanAnswers>(defaults(0))
  const [step, setStep] = useState(0)
  const [result, setResult] = useState<PlanResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (active) listFields().then(setFields).catch((e) => setErr(String(e)))
  }, [active])

  const start = info?.start_year ?? new Date().getFullYear() + 1
  const histYears = [start - 3, start - 2, start - 1]
  const set = <K extends keyof PlanAnswers>(k: K, v: PlanAnswers[K]) => setA((p) => ({ ...p, [k]: v }))

  const pickField = async (f: SavedField) => {
    setErr(null)
    setResult(null)
    setFieldId(f.id)
    fl.setRing(fromPolygon(f.geometry))
    const xs = f.geometry.coordinates[0].map((p) => p[0])
    const ys = f.geometry.coordinates[0].map((p) => p[1])
    fl.fitTo([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], 14)
    try {
      const pf = await getPlannerField(f.id)
      setInfo(pf)
      setA(pf.answers ? { ...defaults(0), ...pf.answers } : defaults(0))
      setStep(1)
    } catch (e) {
      setInfo(null)
      setErr(String(e))
    }
  }

  const run = async () => {
    if (!fieldId) return
    setBusy(true)
    setErr(null)
    try {
      const r = await makePlan(fieldId, a)
      setResult(r)
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  // Language switched: the plan's explanations come from the backend, so fetch the same plan again.
  const planLang = useRef(lang)
  useEffect(() => {
    if (planLang.current === lang) return
    planLang.current = lang
    if (result && fieldId) makePlan(fieldId, a).then(setResult).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang])

  const hasRow = a.consider.some((c) => ROW.includes(c) && !a.avoid.includes(c))
  const steps = useMemo(() => {
    const s = ['field', 'history', 'consider', 'mustAvoid', 'resources', 'prio']
    if (hasRow) s.push('seeds')
    s.push('money', 'soil')
    return s
  }, [hasRow])
  const cur = steps[Math.min(step, steps.length - 1)]
  const last = step >= steps.length - 1
  const optional = ['seeds', 'money', 'soil'].includes(cur)

  if (result && !result.plan.error) {
    return <PlanResult r={result} answers={a} onEdit={() => { setResult(null); setStep(1) }} onRefresh={run} />
  }

  return (
    <div className="stack plan">
      <div className="wiz-progress" aria-label={`${T.step} ${step + 1} ${T.of} ${steps.length}`}>
        {steps.map((s, i) => (
          <button key={s} type="button" className={`dot ${i === step ? 'on' : ''} ${i < step ? 'done' : ''}`}
            disabled={i > 0 && !fieldId} onClick={() => setStep(i)} aria-label={`${T.step} ${i + 1}`} />
        ))}
        <span className="muted small">{T.step} {step + 1} {T.of} {steps.length}</span>
      </div>

      {cur === 'field' && (
        <QCard optional={optional} q={T.q_field} why={T.w_field}>
          {fields === null && <p className="muted">…</p>}
          {fields?.length === 0 && <p className="muted">{T.noFields}</p>}
          <div className="opt-grid">
            {fields?.map((f) => (
              <button key={f.id} type="button" className={`opt ${fieldId === f.id ? 'on' : ''}`} disabled={!f.commune_id} onClick={() => pickField(f)}>
                <b>{f.name}</b>
                <span className="muted small">{f.area_ha != null ? `${fmt(f.area_ha, 1)} ha` : ''}{!f.commune_id ? ` · ${T.outside}` : ''}</span>
              </button>
            ))}
            <button type="button" className="opt add" onClick={goDraw}>{T.drawNew}</button>
          </div>
          {info && <p className="small">{info.field.name}: {fmt(info.field.area_ha, 1)} ha · {info.field.commune}, {info.field.county}</p>}
        </QCard>
      )}

      {cur === 'history' && (
        <QCard optional={optional} q={T.q_history} why={T.w_history}>
          <div className="hist">
            {histYears.map((y) => {
              const h = a.history.find((x) => x.year === y)
              const upd = (crop: PlanCrop | null, yld: number | null) => {
                const rest = a.history.filter((x) => x.year !== y)
                set('history', crop ? [...rest, { year: y, crop, yield_t_ha: yld }].sort((p, q) => p.year - q.year) : rest)
              }
              return (
                <div key={y} className="hist-row">
                  <b>{y}</b>
                  <CropSelect value={h?.crop ?? null} onChange={(c) => upd(c, h?.yield_t_ha ?? null)} none={T.unknown} />
                  <input type="number" step="0.1" min="0" max="25" placeholder={T.yieldOpt} disabled={!h}
                    value={h?.yield_t_ha ?? ''} onChange={(e) => upd(h!.crop, num(e.target.value))} />
                </div>
              )
            })}
          </div>
        </QCard>
      )}

      {cur === 'consider' && (
        <QCard optional={optional} q={T.q_consider} why={T.w_consider}>
          <CropChips value={a.consider} onChange={(v) => set('consider', v)} />
        </QCard>
      )}

      {cur === 'mustAvoid' && (
        <QCard optional={optional} q={T.q_mustAvoid} why={T.w_mustAvoid}>
          <div className="row-wrap">
            <span>{T.mustGrow}:</span>
            <CropSelect value={a.must_grow} onChange={(c) => set('must_grow', c)} none={T.none} />
            {a.must_grow && <>{T.atLeast} <Seg value={a.must_min} options={[[1, '1'], [2, '2']]} onChange={(v) => set('must_min', v)} /> {T.timesIn}</>}
          </div>
          <p className="small" style={{ marginBottom: 4 }}>{T.wontGrow}:</p>
          <CropChips value={a.avoid} onChange={(v) => set('avoid', v)} only={a.consider} />
        </QCard>
      )}

      {cur === 'resources' && (
        <QCard optional={optional} q={T.q_resources} why={T.w_resources}>
          <div className="form-grid">
            <span>{T.irrigation}</span>
            <Seg value={a.irrigation} options={[['yes', T.yes], ['partly', T.partly], ['no', T.no]]} onChange={(v) => set('irrigation', v)} />
            <Toggle label={T.planter} value={a.planter} onChange={(v) => set('planter', v)} />
            <Toggle label={T.combine} value={a.combine} onChange={(v) => set('combine', v)} />
            <span>{T.nLimit}</span>
            <div className="row-wrap">
              <Seg value={a.n_limit === null ? 'any' : 'set'} options={[['any', T.any], ['set', T.kgNha]]}
                onChange={(v) => set('n_limit', v === 'any' ? null : a.n_limit ?? 120)} />
              {a.n_limit !== null && <input type="number" min="0" max="300" step="10" value={a.n_limit} onChange={(e) => set('n_limit', num(e.target.value))} style={{ width: 80 }} />}
            </div>
            <span>{T.contract}</span>
            <div>
              <CropSelect value={a.contract_crop} onChange={(c) => set('contract_crop', c)} none={T.no} />
              <p className="muted small">{T.contractNote}</p>
            </div>
          </div>
        </QCard>
      )}

      {cur === 'prio' && (
        <QCard optional={optional} q={T.q_prio} why={T.w_prio}>
          <PrioritiesPanel value={a.priorities} onChange={(p) => set('priorities', p)} />
          <div className="form-grid">
            <span>{T.riskAtt}</span>
            <Seg value={a.risk} options={[['careful', T.careful], ['balanced', T.balanced], ['bold', T.bold]]} onChange={(v) => set('risk', v)} />
            <span>{T.planLen}</span>
            <Seg value={a.years} options={[[3, `3 ${T.years}`], [4, `4 ${T.years}`]]} onChange={(v) => set('years', v)} />
          </div>
        </QCard>
      )}

      {cur === 'seeds' && (
        <QCard optional={optional} q={T.q_seeds} why={T.w_seeds}>
          <div className="form-grid">
            {(['maize', 'sunflower', 'soy'] as const).filter((c) => a.consider.includes(c) && !a.avoid.includes(c)).map((c) => (
              <div key={c} className="contents">
                <span>{cropName(c, lang)}</span>
                <Seg value={a.maturity[c] ?? 'suggest'} options={[['suggest', T.suggest], ['early', T.early], ['medium', T.medium], ['late', T.late]]}
                  onChange={(v) => set('maturity', { ...a.maturity, [c]: v })} />
              </div>
            ))}
          </div>
        </QCard>
      )}

      {cur === 'money' && (
        <QCard optional={optional} q={T.q_money} why={T.w_money}>
          <div className="money-grid">
            {a.consider.filter((c) => !a.avoid.includes(c)).map((c) => (
              <div key={c} className="contents">
                <span>{cropName(c, lang)}</span>
                <input type="number" min="0" placeholder={`${T.price} (${T.insDefault})`} value={a.prices[c] ?? ''}
                  onChange={(e) => { const v = num(e.target.value); const p = { ...a.prices }; if (v === null) delete p[c]; else p[c] = v; set('prices', p) }} />
                <input type="number" min="0" placeholder={T.cost} value={a.costs[c] ?? ''}
                  onChange={(e) => { const v = num(e.target.value); const p = { ...a.costs }; if (v === null) delete p[c]; else p[c] = v; set('costs', p) }} />
              </div>
            ))}
          </div>
        </QCard>
      )}

      {cur === 'soil' && (
        <QCard optional={optional} q={T.q_soil} why={T.w_soil}>
          <div className="form-grid">
            <span>{T.ph}</span>
            <input type="number" step="0.1" min="3" max="10" value={a.soil_test.ph ?? ''} onChange={(e) => set('soil_test', { ...a.soil_test, ph: num(e.target.value) })} style={{ width: 90 }} />
            <span>{T.soc}</span>
            <input type="number" step="1" min="0" max="200" value={a.soil_test.soc_g_kg ?? ''} onChange={(e) => set('soil_test', { ...a.soil_test, soc_g_kg: num(e.target.value) })} style={{ width: 90 }} />
            <span>{T.texture}</span>
            <select value={a.soil_test.texture ?? ''} onChange={(e) => set('soil_test', { ...a.soil_test, texture: e.target.value || null })}>
              <option value="">—</option>
              {['sand', 'loamy sand', 'sandy loam', 'loam', 'silt loam', 'clay loam', 'silty clay', 'clay'].map((x) => <option key={x}>{x}</option>)}
            </select>
          </div>
          <p className="small" style={{ marginBottom: 4 }}>{T.problemsSeen}:</p>
          <div className="chips">
            {PROBLEMS.map((p) => (
              <button key={p} type="button" className={`chip ${a.problems.includes(p) ? 'on' : ''}`}
                onClick={() => set('problems', a.problems.includes(p) ? a.problems.filter((x) => x !== p) : [...a.problems, p])}>{problem(p)}</button>
            ))}
          </div>
        </QCard>
      )}

      {err && <p className="note warn">{err}</p>}
      {result?.plan.error && <p className="note warn">{result.plan.error}</p>}

      <div className="wiz-nav">
        {step > 0 && <button type="button" onClick={() => setStep(step - 1)}>{T.back}</button>}
        <span style={{ flex: 1 }} />
        {optional && !last && <button type="button" className="ghost" onClick={() => setStep(step + 1)}>{T.skip}</button>}
        {!last && step > 0 && <button type="button" className="primary" onClick={() => setStep(step + 1)}>{T.next}</button>}
        {(last || (step > 0 && fieldId)) && (
          <button type="button" className={last ? 'primary' : 'ghost'} disabled={!fieldId || busy} onClick={run}>{busy ? T.making : T.makePlan}</button>
        )}
      </div>
    </div>
  )
}
