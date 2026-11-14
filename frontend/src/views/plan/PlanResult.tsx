import { useState } from 'react'
import { addHarvestReport } from '../../api/client'
import type { Learning, PlanAnswers, PlanCrop, PlanOption, PlanResponse, PlanYear, PlanProblem } from '../../api/types'
import { fmt } from '../../components/format'
import SourceNote from '../../components/SourceNote'
import { useI18n } from '../../i18n'
import { cropName } from '../../i18n/names'
import { PLAN_CROPS } from './PlanView'
import { PROBLEMS, usePlanText } from './text'

const CROP_COLOR: Record<string, string> = {
  maize: '#f59e0b', wheat: '#d4a017', barley: '#c2a14d', oats: '#a3a35a', pea: '#16a34a',
  chickpea: '#65a30d', sunflower: '#eab308', soy: '#15803d', flax: '#3b82f6',
}
const tenths = (share: number | null | undefined) => (share == null ? '–' : `${Math.round(share * 10)}`)
const lei = (v: number) => `${fmt(v / 1000, 0)}k lei`
const mass = (kg: number) => (kg >= 1000 ? `${fmt(kg / 1000, 1)} t` : `${fmt(kg, 0)} kg`)

function Timeline({ p }: { p: PlanOption }) {
  const { lang } = useI18n()
  return (
    <div className="timeline">
      {p.years.map((y) => (
        <div key={y.year} className="tl-year" style={{ borderTopColor: CROP_COLOR[y.crop] }}>
          <span className="muted small">{y.year}</span>
          <b>{cropName(y.crop, lang)}</b>
        </div>
      ))}
    </div>
  )
}

function ScoreBars({ s }: { s: PlanOption['scores'] }) {
  const { lang } = useI18n()
  const label: Record<string, string> = lang === 'ro'
    ? { yield: 'Producție', water: 'Apă', soil: 'Sol', risk: 'Risc' }
    : { yield: 'Yield', water: 'Water', soil: 'Soil', risk: 'Risk' }
  return (
    <div className="score-bars">
      {(['yield', 'water', 'soil', 'risk'] as const).map((k) => (
        <div key={k} className="sb">
          <span className="small">{label[k] ?? k}</span>
          <div className="sb-track"><div className={`sb-fill ${s[k] >= 70 ? 'good' : s[k] >= 50 ? 'fair' : 'weak'}`} style={{ width: `${s[k]}%` }} /></div>
          <span className="small"><b>{s[k]}</b></span>
        </div>
      ))}
    </div>
  )
}

function YearCard({ y }: { y: PlanYear }) {
  const { T, lang } = usePlanText()
  const [open, setOpen] = useState(false)
  const yl = y.yield
  const winter = y.sowing.kind === 'winter'
  return (
    <div className="year-card" style={{ borderLeftColor: CROP_COLOR[y.crop] }}>
      <div className="yc-head">
        <div>
          <span className="muted small">{y.year}</span>
          <h4>{cropName(y.crop, lang)}{y.maturity && <span className="muted small"> · {y.maturity.label}</span>}</h4>
        </div>
        {yl && (
          <div className="yc-yield">
            <b>{fmt(yl.t_ha, 1)} t/ha</b>
            <span className="muted small">{T.plausible}: {fmt(yl.range_t_ha['80'][0], 1)}–{fmt(yl.range_t_ha['80'][1], 1)}</span>
          </div>
        )}
      </div>

      <div className="kv">
        <span>🌱 {T.sow}</span>
        <span>{winter ? `${y.sowing.window} (${y.year - 1})` : <>{y.sowing.start} – <b>{y.sowing.safe}</b></>}</span>
        <span>🌾 {T.harvest}</span>
        <span>{y.harvest}{y.maturity?.harvest_late ? ` (late years: ${y.maturity.harvest_late})` : ''}</span>
        {yl && <><span>⚖️ {T.tonnes}</span><span><b>{fmt(yl.tonnes, 0)} t</b> <span className="muted">({fmt(yl.range_t['80'][0], 0)}–{fmt(yl.range_t['80'][1], 0)} t)</span></span></>}
        <span>🫘 {T.seed}</span><span>{mass(y.seed.kg[0])}–{mass(y.seed.kg[1])} <span className="muted">({y.seed.kg_ha[0]}–{y.seed.kg_ha[1]} kg/ha)</span></span>
        <span>🧪 {T.nitrogen}</span>
        <span>{y.nitrogen.legume ? T.fixes : <>{mass(y.nitrogen.kg)} N <span className="muted">({fmt(y.nitrogen.kg_ha, 0)} kg/ha)</span>{y.nitrogen.over_limit && <span className="tone-bad"> !</span>}</>}</span>
        <span>💧 {T.water}</span>
        <span>{y.water.irrigated ? T.irrigated : <>{T.rainCoversA} <b className={(y.water.typical_cover_pct ?? 100) < 60 ? 'tone-warn' : ''}>~{y.water.typical_cover_pct ?? '–'} %</b> {T.rainCoversB}{winter && <span className="muted"> · {T.winterWater}</span>}</>}</span>
        <span>⚠️ {T.risks} {y.hazards.stage}</span>
        <span><b className={(y.hazards.any_share ?? 0) >= 0.5 ? 'tone-warn' : ''}>{tenths(y.hazards.any_share)} {T.inYears}</b> <span className="muted">({y.hazards.window})</span></span>
        {y.money
          ? <><span>💰 {T.revenue}</span><span>{lei(y.money.revenue_lei)} <span className="muted">({lei(y.money.revenue_range_lei['80'][0])}–{lei(y.money.revenue_range_lei['80'][1])})</span>
              {y.money.margin_lei != null && <> · {T.margin} <b className={y.money.margin_lei < 0 ? 'tone-bad' : 'tone-good'}>{lei(y.money.margin_lei)}</b></>}</span></>
          : <><span>💰 {T.money}</span><span className="muted">{T.noPrice}</span></>}
      </div>

      <button type="button" className="link small" onClick={() => setOpen(!open)}>{open ? '▾' : '▸'} details</button>
      {open && (
        <div className="small stack-tight">
          <p>{y.sowing.text}{y.sowing.frost_after_safe ? ` Frost after that date: ${y.sowing.frost_after_safe} of ${y.sowing.n_years} years.` : ''}</p>
          {yl && <p>{T.expected}: {T.likely} {fmt(yl.range_t_ha['50'][0], 1)}–{fmt(yl.range_t_ha['50'][1], 1)} t/ha · {yl.basis}{yl.proxy ? ` (proxy: ${yl.proxy})` : ''}{yl.adjustments.length ? ` · ${yl.adjustments.join('; ')}` : ''}. Confidence: {yl.confidence}.</p>}
          {y.maturity_options.length > 0 && (
            <table className="mini">
              <thead><tr><th>{T.options}</th><th>{T.harvest}</th><th>{T.beforeFrost}</th><th>{T.wetHarvest}</th></tr></thead>
              <tbody>
                {y.maturity_options.map((m) => (
                  <tr key={m.class} className={m.class === y.maturity_chosen ? 'on' : ''}>
                    <td>{m.label}{m.class === y.maturity_suggested ? ' ★' : ''}</td><td>{m.harvest ?? '–'}</td>
                    <td>{tenths(m.before_frost_share)}/10</td><td>{tenths(m.wet_harvest_share)}/10</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p>{T.water}: need {y.water.need_mm[0]}–{y.water.need_mm[1]} mm; Apr–Sep rain {fmt(y.water.rain_median_mm, 0)} mm in a typical year; covered the full need in {tenths(y.water.covers_mid_share)}/10 seasons. {y.water.note}</p>
          <ul>{y.hazards.per_hazard.map((h) => <li key={h.key}>{h.text}: {h.hits} of {h.years} years</li>)}</ul>
          <p className="muted">{y.quality_note}{y.money ? ` · Price: ${fmt(y.money.price_lei_t, 0)} lei/t (${y.money.price_source}).` : ''}</p>
        </div>
      )}
    </div>
  )
}

function LearningCard({ l, fieldId, start, onSaved }: { l: Learning; fieldId: number; start: number; onSaved: (l: Learning) => void }) {
  const { T, problem, lang } = usePlanText()
  const [r, setR] = useState<{ year: number; crop: PlanCrop; yield_t_ha: string; maturity: string; irrigated: boolean; problems: PlanProblem[] }>(
    { year: start - 1, crop: 'maize', yield_t_ha: '', maturity: '', irrigated: false, problems: [] })
  const [msg, setMsg] = useState<string | null>(null)
  const save = async () => {
    setMsg(null)
    try {
      const res = await addHarvestReport(fieldId, {
        year: r.year, crop: r.crop, yield_t_ha: r.yield_t_ha === '' ? null : Number(r.yield_t_ha),
        maturity: r.maturity || null, irrigated: r.irrigated, problems: r.problems,
      })
      onSaved(res.learning)
      setMsg(T.saved)
    } catch (e) {
      setMsg(String(e))
    }
  }
  const eff = (k: 'legume_precrop_yield_bonus' | 'repeat_penalty', label: string) => {
    const e = l.shared[k]
    return <li>{label}: {T.literature} {fmt(100 * e.literature, 0)} % → {T.measured} {e.measured == null ? '–' : `${fmt(100 * e.measured, 0)} %`} ({e.n}) → <b>{T.used} {fmt(100 * e.used, 1)} %</b></li>
  }
  return (
    <div className="wiz-card">
      <h3>{T.learning}</h3>
      <p className="lead">
        {T.yourField}: {l.field.n === 0 ? <span className="muted">{T.noReports}</span>
          : <><b className={l.field.pct >= 0 ? 'tone-good' : 'tone-warn'}>{l.field.pct >= 0 ? '+' : ''}{fmt(l.field.pct, 0)} %</b> <span className="muted small">
              ({l.field.n} seasons; raw {l.field.raw_pct! >= 0 ? '+' : ''}{fmt(l.field.raw_pct, 0)} %, trusted {Math.round(100 * l.field.weight)} % so far)</span></>}
      </p>
      {l.field.seasons.length > 0 && (
        <div className="chips">{l.field.seasons.map((s) => <span key={s.year} className="chip static">{s.year} {cropName(s.crop, lang)} {fmt(s.yield_t_ha, 1)} t/ha · {s.vs_county_pct >= 0 ? '+' : ''}{s.vs_county_pct} %</span>)}</div>
      )}
      <p className="small" style={{ marginBottom: 2 }}><b>{T.shared}</b> <span className="muted">({l.shared.n_reports} {l.shared.n_reports === 1 ? 'report' : 'reports'}, {l.shared.n_fields} {l.shared.n_fields === 1 ? 'field' : 'fields'})</span></p>
      <ul className="small">{eff('legume_precrop_yield_bonus', T.legBonus)}{eff('repeat_penalty', T.repeatPen)}</ul>

      <h4 style={{ marginTop: 8 }}>{T.report}</h4>
      <div className="report-form">
        <input type="number" value={r.year} min={2000} max={start} onChange={(e) => setR({ ...r, year: Number(e.target.value) })} style={{ width: 80 }} />
        <select value={r.crop} onChange={(e) => setR({ ...r, crop: e.target.value as PlanCrop })}>
          {PLAN_CROPS.map((c) => <option key={c} value={c}>{cropName(c, lang)}</option>)}
        </select>
        <input type="number" step="0.1" min="0" max="25" placeholder="t/ha" value={r.yield_t_ha} onChange={(e) => setR({ ...r, yield_t_ha: e.target.value })} style={{ width: 80 }} />
        {['maize', 'sunflower', 'soy'].includes(r.crop) && (
          <select value={r.maturity} onChange={(e) => setR({ ...r, maturity: e.target.value })}>
            <option value="">{T.maturity}…</option><option value="early">{T.early}</option><option value="medium">{T.medium}</option><option value="late">{T.late}</option>
          </select>
        )}
        <label className="toggle small"><input type="checkbox" checked={r.irrigated} onChange={(e) => setR({ ...r, irrigated: e.target.checked })} /> {T.irrigated.split(' —')[0]}</label>
      </div>
      <div className="chips">
        {PROBLEMS.map((p) => (
          <button key={p} type="button" className={`chip ${r.problems.includes(p) ? 'on' : ''}`}
            onClick={() => setR({ ...r, problems: r.problems.includes(p) ? r.problems.filter((x) => x !== p) : [...r.problems, p] })}>{problem(p)}</button>
        ))}
      </div>
      <div><button type="button" className="primary" onClick={save}>{T.reportBtn}</button> {msg && <span className="small">{msg}</span>}</div>
    </div>
  )
}

export default function PlanResult({ r, answers, onEdit, onRefresh }: { r: PlanResponse; answers: PlanAnswers; onEdit: () => void; onRefresh: () => void }) {
  const { T, lang } = usePlanText()
  const [k, setK] = useState(0)
  const [learning, setLearning] = useState(r.learning)
  const plans = r.plan.plans
  const p = plans[Math.min(k, plans.length - 1)]
  const end = r.plan.start_year + p.crops.length - 1
  const why = [...(p.factors.soil ?? []), ...(p.factors.yield ?? [])].filter((f) => f.effect !== '·').slice(0, 5)
  const s = r.season
  return (
    <div className="stack plan">
      <div className="wiz-card">
        <div className="yc-head">
          <div>
            <span className="muted small">{r.field.name} · {fmt(r.field.area_ha, 1)} ha · {r.field.commune}, {r.field.county}</span>
            <h3>{T.yourPlan} {r.plan.start_year}–{end}</h3>
          </div>
          <button type="button" onClick={onEdit}>{T.edit}</button>
        </div>
        <div className="seg big">
          {plans.map((_, i) => <button key={i} type="button" className={i === k ? 'on' : ''} onClick={() => setK(i)}>{[T.planA, T.planB, T.planC][i]}</button>)}
        </div>
        <Timeline p={p} />
        <ScoreBars s={p.scores} />
        <p className="muted small">{T.score} {p.score}{p.contract_bonus ? ` (incl. +${p.contract_bonus} contract crop)` : ''} · {fmt(r.plan.sequences_checked, 0)} {T.checked}</p>
        {why.length > 0 && (
          <>
            <p className="small" style={{ marginBottom: 2 }}><b>{T.whyPlan}:</b></p>
            <ul className="small">{why.map((f, i) => <li key={i}><span className={f.effect === '+' ? 'tone-good' : 'tone-warn'}>{f.effect}</span> {f.label}: {f.value}</li>)}</ul>
          </>
        )}
        {r.plan.notes.map((n, i) => <p key={i} className="note small">{n}</p>)}
      </div>

      {p.years.map((y) => <YearCard key={y.year} y={y} />)}

      <div className="wiz-card">
        <h3>{T.totals}</h3>
        <div className="tiles">
          <div className="tile"><span className="tile-label">{T.seed}</span><span className="tile-value">{fmt(p.totals.seed_kg / 1000, 1)} t</span></div>
          <div className="tile"><span className="tile-label">{T.nitrogen}</span><span className="tile-value">{fmt(p.totals.nitrogen_kg / 1000, 1)} t N</span></div>
          {p.totals.revenue_lei != null && <div className="tile"><span className="tile-label">{T.revenue}</span><span className="tile-value">{lei(p.totals.revenue_lei)}</span></div>}
        </div>
      </div>

      {s && (
        <div className="wiz-card">
          <h3>{T.thisSeason} {s.year}: {cropName(s.crop, lang)}</h3>
          {s.county_forecast && (
            <p className="small">County forecast {fmt(s.county_forecast.t_ha, 1)} t/ha (8 in 10: {fmt(s.county_forecast.range_80_t_ha[0], 1)}–{fmt(s.county_forecast.range_80_t_ha[1], 1)}; weather signal {s.county_forecast.signal})
              {s.your_yield_t_ha != null && <> · yours: <b>{fmt(s.your_yield_t_ha, 1)} t/ha</b></>}.</p>
          )}
          {s.quality && (
            <p className={`note ${s.quality.level === 'elevated' ? 'warn' : ''} small`}>
              {s.quality.level === 'elevated'
                ? <>Quality risk elevated: {s.quality.hits.map((h) => h.text).join('; ')}. {s.quality.quality} Test lots (e.g. mycotoxins) before selling or feeding.</>
                : <>No weather-related quality warning for this crop in {s.year}.</>}
            </p>
          )}
        </div>
      )}

      <LearningCard l={learning} fieldId={r.field.id} start={r.plan.start_year} onSaved={(l) => { setLearning(l); onRefresh() }} />

      <SourceNote
        source="NASA POWER 2000–2026; INS TEMPO yields (AGR110A) and farm-gate prices (PPA102C); crop traits (FAO, IPCC, agronomy); your answers and reports"
        period={`${r.plan.start_year}–${end}`}
        resolution="county weather & statistics × your field"
        confidence="low"
        note={`Planning aid, not a guarantee. ${answers.irrigation === 'yes' ? 'Irrigated: water weight set to 0. ' : ''}Ranges come from how far past years fell from the county trend; the field's own level is learned from your reports.`}
        assumptions={r.method}
      />
    </div>
  )
}
