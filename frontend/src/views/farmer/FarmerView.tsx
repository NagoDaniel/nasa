import { useState } from 'react'
import { getArea } from '../../api/client'
import type { Priorities } from '../../api/types'
import Card from '../../components/Card'
import { PALETTE } from '../../components/Chart'
import { useAsync } from '../../components/useAsync'
import { useI18n } from '../../i18n'
import CropMixCard from './CropMixCard'
import CropStatsCard from './CropStatsCard'
import IndicatorCard from './IndicatorCard'
import PrioritiesPanel from './PrioritiesPanel'
import RotationCompare from './RotationCompare'
import SeasonEvents from './SeasonEvents'
import SoilCard from './SoilCard'

const MAIN = ['imerg_precip', 'modis_ndvi', 'smap_soil_moisture', 'gldas_rootmoist', 'power_heat_days', 'modis_et', 'grace_tws', 'firms_fires']
const COLORS: Record<string, string> = {
  imerg_precip: PALETTE[0], gldas_rootmoist: PALETTE[5], power_heat_days: PALETTE[4], modis_et: PALETTE[2],
  firms_fires: PALETTE[1], grace_tws: PALETTE[7], modis_ndvi: PALETTE[6], smap_soil_moisture: PALETTE[3],
}

export default function FarmerView({ unitId, countyName }: { unitId: string; countyName: string }) {
  const { t } = useI18n()
  const area = useAsync(unitId, () => getArea(unitId))
  const [prio, setPrio] = useState<Priorities>({ yield: 25, water: 25, soil: 25, risk: 25 })
  const [more, setMore] = useState(false)

  if (area.error) return <p className="note warn">{t('error')}: {area.error}</p>
  if (!area.data) return <p className="muted pad">{t('loading')}</p>
  const a = area.data
  const kind = a.unit.kind
  const main = a.indicators.filter((i) => MAIN.includes(i.name))
  const rest = a.indicators.filter((i) => !MAIN.includes(i.name))

  return (
    <div className={`view ${area.loading ? 'stale' : ''}`}>
      <h2 className="section">{t('whatHappened')}</h2>
      <p className="muted small section-sub">{t('whatHappenedSub')}</p>
      <div className="grid">
        {main.map((ind, i) => <IndicatorCard key={ind.name} ind={ind} color={COLORS[ind.name] ?? PALETTE[i % PALETTE.length]} kind={kind} />)}
        {more && rest.map((ind, i) => <IndicatorCard key={ind.name} ind={ind} color={PALETTE[(i + 3) % PALETTE.length]} kind={kind} />)}
      </div>
      <button className="ghost" onClick={() => setMore(!more)}>{more ? '−' : '+'} {rest.length} more indicators</button>

      <SeasonEvents agro={a.agro_yearly} kind={kind} />
      <div className="grid two">
        <SoilCard soil={a.soil} terrain={a.terrain} kind={kind} />
        <CropStatsCard stats={a.crop_stats} countyName={countyName} />
      </div>
      {a.cropmap && <CropMixCard cm={a.cropmap} stats={a.crop_stats} kind={kind} />}

      <PrioritiesPanel value={prio} onChange={setPrio} />
      <RotationCompare unitId={unitId} priorities={prio} />

      <Card title={t('aiTitle')} className="muted-card"><p className="muted small">{t('aiBody')}</p></Card>
    </div>
  )
}
