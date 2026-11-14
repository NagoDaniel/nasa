import type { AreaBundle } from '../../api/types'
import { fmt } from '../../components/format'
import StatTile from '../../components/StatTile'
import { useI18n } from '../../i18n'
import type { Dict } from '../../i18n/en'
import { useExplain } from '../../i18n/explain'
import { sameSpec, useMapLink, type LayerSpec } from '../../state/MapLink'
import type { FarmerSection } from '../../state/sections'
import { arableClasses } from './CropMixCard'
import { RISK_ROWS, isHit } from './SeasonEvents'
import { latestComplete } from './series'

export type OverviewPick = { spec: LayerSpec; year?: string }

/** Headline numbers for the area. Each tile recolours the map; each group links to its section. */
export default function Overview({ a, pick, onPick }: { a: AreaBundle; pick: OverviewPick; onPick: (p: OverviewPick) => void }) {
  const { t } = useI18n()
  const x = useExplain()
  const { goTo } = useMapLink()
  const ind = (n: string) => a.indicators.find((i) => i.name === n)
  const agro = a.agro_yearly
  const lastIdx = agro.years.length - 1
  const lastYear = agro.years[lastIdx]
  const agroVal = (k: string) => agro.values[k]?.[lastIdx] ?? null
  const on = (spec: LayerSpec) => sameSpec(pick.spec, spec)
  const tile = (spec: LayerSpec, year?: string | number) => ({ active: on(spec), onClick: () => onPick({ spec, year: year === undefined ? undefined : String(year) }) })

  const rain = latestComplete(ind('imerg_precip'))
  const rainDiff = rain ? Math.round((100 * (rain.value - rain.avg)) / rain.avg) : 0
  const hot = latestComplete(ind('power_heat_days'))
  const z = agroVal('rootmoist_jja_z')
  const veryHot = agroVal('heat35_jul_aug')
  const zText = z === null ? '–' : z <= -1 ? t('muchDrier') : z <= -0.5 ? t('drier') : z < 0.5 ? t('normal') : t('wetter')

  const soil = a.soil.values
  const ph = soil?.phh2o?.median
  const soc = soil?.soc?.median
  const clay = soil?.clay?.median

  const cm = a.cropmap?.values
  const cmYear = a.cropmap ? a.cropmap.years[a.cropmap.years.length - 1] : null
  const arable = cmYear ? arableClasses(cm?.[cmYear]) : []
  const arableTotal = arable.reduce((s, [, n]) => s + n, 0)
  const topCrop = [...arable].sort((p, q) => q[1] - p[1])[0]
  const pulses = cmYear ? cm?.[cmYear]?.['240'] ?? 0 : 0

  const alerts = RISK_ROWS.filter((k) => agro.values[k] && isHit(agro, k, agroVal(k)))

  const Group = ({ title, to }: { title: string; to: FarmerSection }) => (
    <div className="group-head">
      <h3>{title}</h3>
      <button type="button" className="link" onClick={() => goTo(to)}>{t('open')} →</button>
    </div>
  )

  return (
    <div className="stack">
      <Group title={t('nav_weather')} to="weather" />
      <div className="tiles">
        {rain && (
          <StatTile
            label={`${t('rainIn')} ${rain.year}`} value={fmt(rain.value)} unit="mm"
            note={Math.abs(rainDiff) < 5 ? t('nearAvg') : `${Math.abs(rainDiff)}% ${t(rainDiff < 0 ? 'belowAvg' : 'aboveAvg')}`}
            tone={rainDiff <= -10 ? 'warn' : 'neutral'} info={x.indicators.imerg_precip}
            {...tile({ kind: 'indicator', key: 'imerg_precip' }, rain.year)}
          />
        )}
        {hot && (
          <StatTile
            label={`${t('hotDaysIn')} ${hot.year}`} value={fmt(hot.value)} unit={t('days')}
            note={`${t('avgShort')} ${fmt(hot.avg)}`} tone={hot.value > hot.avg * 1.25 ? 'warn' : 'neutral'} info={x.indicators.power_heat_days}
            {...tile({ kind: 'indicator', key: 'power_heat_days' }, hot.year)}
          />
        )}
        <StatTile
          label={`${t('summerSoil')} ${lastYear}`} value={zText}
          note={z === null ? undefined : `z = ${fmt(z, 1)}`} tone={z !== null && z <= -1 ? 'bad' : z !== null && z <= -0.5 ? 'warn' : 'neutral'}
          info={x.agro.rootmoist_jja_z} {...tile({ kind: 'agro', key: 'rootmoist_jja_z' }, lastYear)}
        />
        <StatTile
          label={`${t('veryHot')} ${lastYear}`} value={fmt(veryHot)} unit={t('days')}
          note={t('riskFrom')} tone={veryHot !== null && veryHot >= 3 ? 'bad' : 'neutral'}
          info={x.agro.heat35_jul_aug} {...tile({ kind: 'agro', key: 'heat35_jul_aug' }, lastYear)}
        />
      </div>

      <Group title={`${t('alertsIn')} ${lastYear}`} to="risks" />
      {alerts.length === 0
        ? <p className="muted">{t('noAlerts')}</p>
        : (
          <div className="chips">
            {alerts.map((k) => (
              <button
                key={k} type="button" className={`chip alert ${on({ kind: 'agro', key: k }) ? 'on' : ''}`}
                onClick={() => onPick({ spec: { kind: 'agro', key: k }, year: String(lastYear) })}
              >
                {agro.indicators[k].label}
              </button>
            ))}
          </div>
        )}

      <Group title={t('nav_soil')} to="soil" />
      <div className="tiles">
        {ph !== undefined && (
          <StatTile
            label={t('soilPh')} value={fmt(ph, 1)} note={t(ph < 6 ? 'phAcid' : 'phOk')} tone={ph < 6 ? 'warn' : 'good'}
            info={x.soil.phh2o} {...tile({ kind: 'soil', key: 'phh2o' })}
          />
        )}
        {soc !== undefined && (
          <StatTile
            label={t('organicCarbon')} value={fmt(soc, 0)} unit="g/kg"
            note={t((soc < 10 ? 'socLow' : soc < 20 ? 'socMid' : 'socGood') as keyof Dict)} tone={soc < 10 ? 'warn' : 'good'}
            info={x.soil.soc} {...tile({ kind: 'soil', key: 'soc' })}
          />
        )}
        {soil?.texture && (
          <StatTile
            label={t('texture')} value={soil.texture} note={clay !== undefined ? `${fmt(clay)}% ${t('clayShare')}` : undefined}
            info={x.soil.texture} {...tile({ kind: 'soil', key: 'clay' })}
          />
        )}
      </div>

      {a.cropmap && topCrop && cmYear && (
        <>
          <Group title={t('nav_crops')} to="crops" />
          <div className="tiles">
            <StatTile
              label={`${t('mainCrop')} (${cmYear})`} value={a.cropmap.classes[topCrop[0]]}
              note={`${fmt((100 * topCrop[1]) / (arableTotal || 1))}% ${t('ofArable')}`}
              info={x.cropMix.pct} {...tile({ kind: 'cropshare', key: topCrop[0] }, cmYear)}
            />
            <StatTile
              label={`${t('legumeShare')} (${cmYear})`} value={fmt((100 * pulses) / (arableTotal || 1), 1)} unit="%"
              note={t('ofArable')} info={x.cropMix.legumes} {...tile({ kind: 'cropshare', key: '240' }, cmYear)}
            />
          </div>
        </>
      )}
      <p className="hint">{t('hintTile')}</p>
    </div>
  )
}
