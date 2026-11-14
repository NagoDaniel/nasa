import type { Lang } from './index'

export const CROPS = ['maize', 'barley', 'oats', 'pea', 'chickpea', 'flax', 'sunflower', 'wheat', 'soy'] as const
export type CropId = (typeof CROPS)[number]
/** Direction B (SMART FEED) ingredient crops. */
export const B_CROPS: CropId[] = ['oats', 'barley', 'maize', 'pea', 'chickpea', 'flax', 'sunflower']

const CROP_NAMES: Record<string, { en: string; ro: string }> = {
  maize: { en: 'Maize', ro: 'Porumb' },
  barley: { en: 'Barley', ro: 'Orz' },
  oats: { en: 'Oats', ro: 'Ovăz' },
  pea: { en: 'Pea', ro: 'Mazăre' },
  chickpea: { en: 'Chickpea', ro: 'Năut' },
  flax: { en: 'Flax (oil)', ro: 'In pentru ulei' },
  sunflower: { en: 'Sunflower', ro: 'Floarea-soarelui' },
  wheat: { en: 'Wheat', ro: 'Grâu' },
  soy: { en: 'Soybean', ro: 'Soia' },
  grain_legumes: { en: 'Grain legumes', ro: 'Leguminoase boabe' },
  rapeseed: { en: 'Rapeseed', ro: 'Rapiță' },
}

export const cropName = (id: string, lang: Lang) => CROP_NAMES[id]?.[lang] ?? id

/** Romanian labels for backend indicator labels (English comes from the data). */
const INDICATOR_RO: Record<string, string> = {
  imerg_precip: 'Precipitații (satelit)',
  gldas_rootmoist: 'Umiditatea solului în zona rădăcinilor (0–100 cm)',
  power_heat_days: 'Zile caniculare (Tmax ≥ 32 °C)',
  gldas_et: 'Evapotranspirație',
  power_tmax: 'Temperatura maximă medie',
  firms_fires: 'Incendii de vegetație detectate',
  modis_ndvi: 'Indicele de vegetație pe teren agricol (NDVI)',
  modis_ndvi_all: 'Indicele de vegetație, tot terenul (NDVI)',
  smap_soil_moisture: 'Umiditatea solului la suprafață (satelit, 0–5 cm)',
  modis_et: 'Evapotranspirație pe teren agricol (satelit)',
  modis_pet: 'Evapotranspirație potențială pe teren agricol (satelit)',
  modis_lst_day: 'Temperatura suprafeței solului ziua, teren agricol',
  modis_lst_night: 'Temperatura suprafeței solului noaptea, teren agricol',
  grace_tws: 'Anomalia rezervei totale de apă (GRACE)',
  power_precip: 'Precipitații (POWER)',
  gldas_soilmoist_0_10: 'Umiditatea solului (0–10 cm)',
  gldas_pet: 'Evaporare potențială',
  gldas_rain: 'Ploaie (model)',
  power_tmean: 'Temperatura medie',
  power_frost_days: 'Zile cu îngheț (Tmin < 0 °C)',
  power_gdd10: 'Grade-zile de creștere (bază 10 °C)',
  power_rh: 'Umiditatea relativă',
  power_soil_wetness: 'Umiditatea solului (POWER)',
}
export const indicatorLabel = (name: string, fallback: string, lang: Lang) =>
  lang === 'ro' ? INDICATOR_RO[name] ?? fallback : fallback
