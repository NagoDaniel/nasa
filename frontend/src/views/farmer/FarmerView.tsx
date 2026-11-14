import { useEffect, useState } from 'react'
import { getArea } from '../../api/client'
import type { Priorities } from '../../api/types'
import { PALETTE } from '../../components/Chart'
import Collapsible from '../../components/Collapsible'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import { useExplain } from '../../i18n/explain'
import { indicatorLabel } from '../../i18n/names'
import { useMapLink } from '../../state/MapLink'
import type { FarmerSection } from '../../state/sections'
import CropMixCard from './CropMixCard'
import CropStatsCard from './CropStatsCard'
import IndicatorChart from './IndicatorChart'
import Overview, { type OverviewPick } from './Overview'
import PrioritiesPanel from './PrioritiesPanel'
import RotationCompare, { PRESETS, type Rot } from './RotationCompare'
import SeasonEvents from './SeasonEvents'
import SoilCard from './SoilCard'

const MAIN = ['imerg_precip', 'gldas_rootmoist', 'power_heat_days', 'gldas_et', 'power_tmax', 'firms_fires', 'modis_ndvi']
const COLORS: Record<string, string> = {
  imerg_precip: PALETTE[0], gldas_rootmoist: PALETTE[5], power_heat_days: PALETTE[4], gldas_et: PALETTE[2],
  firms_fires: PALETTE[1], power_tmax: PALETTE[7], modis_ndvi: PALETTE[6],
}

/** One section at a time; the choices made in each section are kept while you move around. */
export default function FarmerView({ unitId, countyName, section, active }: {
  unitId: string
  countyName: string
  section: FarmerSection
  /** False while the procurement role is shown (this view stays mounted to keep its state). */
  active: boolean
}) {
  const { t, lang } = useI18n()
  const x = useExplain()
  const { setSpec } = useMapLink()
  const area = useAsync(unitId, () => getArea(unitId))
  const [prio, setPrio] = useState<Priorities>({ yield: 25, water: 25, soil: 25, risk: 25 })
  const [rots, setRots] = useState<Rot[]>(PRESETS.slice(0, 2))
  const [overview, setOverview] = useState<OverviewPick>({ spec: { kind: 'indicator', key: 'imerg_precip' } })
  const [indicator, setIndicator] = useState('imerg_precip')
  const [risk, setRisk] = useState('heat35_jul_aug')
  const [soilProp, setSoilProp] = useState('phh2o')
  const [crop, setCrop] = useState('216')
  const [more, setMore] = useState(false)

  // The map follows the section: it is coloured by whatever is selected here.
  useEffect(() => {
    if (!active) return
    if (section === 'overview') setSpec(overview.spec, overview.year)
    else if (section === 'weather') setSpec({ kind: 'indicator', key: indicator })
    else if (section === 'risks') setSpec({ kind: 'agro', key: risk })
    else if (section === 'soil') setSpec({ kind: 'soil', key: soilProp })
    else if (section === 'crops') setSpec({ kind: 'cropshare', key: crop })
    else setSpec(null)
  }, [active, section, overview, indicator, risk, soilProp, crop, setSpec])

  if (area.error) return <p className="note warn">{t('error')}: {area.error}</p>
  if (!area.data) return <p className="muted pad">{t('loading')}</p>
  const a = area.data
  const kind = a.unit.kind
  const main = a.indicators.filter((i) => MAIN.includes(i.name))
  const rest = a.indicators.filter((i) => !MAIN.includes(i.name))
  const current = a.indicators.find((i) => i.name === indicator) ?? a.indicators[0]

  return (
    <div className={`view ${area.loading ? 'stale' : ''}`}>
      {section === 'overview' && <Overview a={a} pick={overview} onPick={setOverview} />}

      {section === 'weather' && (
        <div className="stack">
          <div className="chips">
            {[...main, ...(more ? rest : [])].map((i) => (
              <button key={i.name} type="button" className={`chip ${i.name === current.name ? 'on' : ''}`} onClick={() => setIndicator(i.name)}>
                {indicatorLabel(i.name, i.label, lang)}
              </button>
            ))}
            <button type="button" className="link" onClick={() => setMore(!more)}>
              {more ? `− ${t('less')}` : `+ ${rest.length} ${t('moreIndicators')}`}
            </button>
          </div>
          <IndicatorChart key={current.name} ind={current} color={COLORS[current.name] ?? PALETTE[3]} kind={kind} />
        </div>
      )}

      {section === 'risks' && <SeasonEvents agro={a.agro_yearly} kind={kind} selected={risk} onSelect={setRisk} />}

      {section === 'soil' && <SoilCard soil={a.soil} kind={kind} selected={soilProp} onSelect={setSoilProp} />}

      {section === 'crops' && (
        <div className="stack">
          {a.cropmap && (
            <Collapsible id="crops-mix" title={t('cropMixTitle')} info={x.cropMix.ha} defaultOpen>
              <CropMixCard cm={a.cropmap} stats={a.crop_stats} kind={kind} selected={crop} onSelect={setCrop} />
            </Collapsible>
          )}
          <Collapsible id="crops-yields" title={`${t('countyYields')}: ${countyName}`} info={x.cropStats}>
            <CropStatsCard stats={a.crop_stats} />
          </Collapsible>
        </div>
      )}

      {section === 'rotations' && (
        <div className="stack">
          <Collapsible id="rot-priorities" title={t('priorities')} info={x.priorities} defaultOpen>
            <PrioritiesPanel value={prio} onChange={setPrio} />
          </Collapsible>
          <Collapsible id="rot-compare" title={t('rotations')} info={x.general.scoreScale} defaultOpen>
            <RotationCompare unitId={unitId} priorities={prio} rots={rots} setRots={setRots} />
          </Collapsible>
          <p className="muted small"><b>{t('aiTitle')}:</b> {t('aiBody')}</p>
        </div>
      )}
    </div>
  )
}
