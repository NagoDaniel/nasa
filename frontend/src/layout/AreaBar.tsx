import { useMemo } from 'react'
import type { Unit } from '../api/types'
import { fmt } from '../components/format'
import { useI18n } from '../i18n'

/** Pick the area by name (the map is the other way to pick it). */
export default function AreaBar({ units, selectedId, onSelect, notice }: {
  units: Unit[]
  selectedId: string
  onSelect: (id: string) => void
  notice: string | null
}) {
  const { t, lang } = useI18n()
  const sel = units.find((u) => u.id === selectedId)
  const county = sel?.county ?? selectedId.split('-')[0]
  const counties = useMemo(() => units.filter((u) => u.kind === 'county').sort((a, b) => a.name.localeCompare(b.name, 'ro')), [units])
  const communes = useMemo(
    () => units.filter((u) => u.kind === 'commune' && u.county === county).sort((a, b) => a.name.localeCompare(b.name, 'ro')),
    [units, county],
  )
  return (
    <div className="areabar">
      <label>
        <span>{t('county')}</span>
        <select value={county} onChange={(e) => onSelect(e.target.value)}>
          {counties.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <label>
        <span>{t('commune')}</span>
        <select value={sel?.kind === 'commune' ? sel.id : ''} onChange={(e) => onSelect(e.target.value || county)}>
          <option value="">{t('wholeCounty')}</option>
          {communes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      {sel && <span className="area-size">{fmt(sel.area_km2)} km²</span>}
      {notice
        ? <span className="area-notice">{notice} {t('outsideAoi')}</span>
        : <span className="area-hint">{lang === 'ro' ? 'sau alegeți pe hartă' : 'or pick it on the map'}</span>}
    </div>
  )
}
