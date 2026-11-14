export type Confidence = { county: string; commune: string; note: string }

export type Unit = {
  id: string
  kind: 'county' | 'commune'
  name: string
  county: string
  area_km2: number
  point: [number, number]
}

export type Indicator = {
  name: string
  label: string
  source: string
  variable: string
  unit: string
  aggregation: 'sum' | 'mean'
  period: { start: string; end: string; step: string }
  resolution: string
  confidence: Confidence
  status: 'complete' | 'sample'
  missing_periods?: string[]
  keys: string[]
  values: (number | null)[]
}

export type AgroYearly = {
  years: number[]
  indicators: Record<string, { label: string; unit: string; source: string; window: string; why: string }>
  confidence: Confidence
  hazards: Record<string, { op: '>=' | '<='; threshold: number; text: string }>
  values: Record<string, (number | null)[]>
}

export type Stat = { median: number; p10: number; p90: number }
export type Soil = {
  source: string
  depth: string
  resolution: string
  properties: Record<string, { label: string; unit: string }>
  confidence: Confidence
  values: (Record<string, Stat | null> & { texture?: string; valid_share: number; pixels: number }) | null
}

export type CropSeries = { area_ha?: (number | null)[]; production_t?: (number | null)[]; yield_kg_ha?: (number | null)[] }

export type AreaBundle = {
  unit: Unit
  indicators: Indicator[]
  agro_yearly: AgroYearly
  soil: Soil
  terrain: null | Terrain
  cropmap: null | CropMap
  crop_stats: { source: string; years: number[]; confidence: Confidence; county: string; values: Record<string, CropSeries> }
}

export type CropMap = {
  source: string
  resolution: string
  unit: string
  classes: Record<string, string>
  crop_codes: Record<string, string>
  years: string[]
  confidence: Confidence
  values: Record<string, Record<string, number>> | null
}

export type Priorities = { yield: number; water: number; soil: number; risk: number }

export type Factor = { label: string; value: string; effect: '+' | '−' | '·'; source: string; assumption: string | null }

export type RotationResult = {
  name: string
  crops: string[]
  scores: Priorities
  total: number
  weights: Priorities
  years: { year: number; crop: string; yield: number; water: number; risk: number; expected_yield_kg_ha: [number | null, number | null]; effects: string[] }[]
  factors: Record<keyof Priorities, Factor[]>
  confidence: { level: string; notes: string[] }
}

export type ScoreResponse = { unit: Unit; priorities: Priorities; results: RotationResult[] }

export type CountyProcurement = {
  name: string
  confidence: string
  availability: {
    score: number
    production_t_median_5y: number | null
    latest_t: number | null
    latest_vs_median_pct: number | null
    area_ha_latest: number | null
    area_trend_pct_yr: number | null
    yield_cv: number | null
    hazard_years: number
    years: number
    series: { years: number[]; production_t: (number | null)[]; area_ha: (number | null)[]; yield_kg_ha: (number | null)[] }
  }
  quality: { score: number; hazard_freq: number | null; bad_years: Record<string, string[]>; latest_year: number | null; latest_hits: string[] }
  impact: {
    score: number | null
    water_score: number | null
    water_need_mm: [number, number]
    dry_year_rain_mm: number | null
    emissions_kg_co2e_t: number | null
    yield_kg_ha_5y: number | null
    legume_share_pct: number | null
    fires_per_1000ha_yr: number | null
  }
}

export type Recommendation = { type: string; title: string; text: string; numbers: Record<string, unknown>; assumptions?: string[] }

export type ProcurementResponse = {
  crop: string
  proxy: string | null
  counties: Record<string, CountyProcurement>
  recommendations: Recommendation[]
  outlook: Forecast | null
  assumptions: string[]
  sources: string[]
}

export type MapLayerData = {
  kind: 'indicator' | 'agro' | 'soil' | 'cropshare'
  key: string
  label: string
  unit: string
  years: string[] | null
  values: Record<string, (number | null)[]>
  palette: 'blue' | 'red' | 'green' | 'brown' | 'div'
  source: string
}

export type Terrain = {
  sources: { terrain: string; landcover: string }
  resolution: { terrain: string; landcover: string }
  steep_threshold_pct: number
  classes: Record<string, string>
  confidence: Confidence
  values: {
    elevation_m?: number
    slope_pct?: number
    steep_share_pct?: number
    cropland_slope_pct?: number
    cropland_steep_share_pct?: number
    landcover_pct?: Record<string, number>
  }
}

export type ForecastModel = {
  predictors: { key: string; label: string; unit: string; effect_pct_per_unit: number }[]
  n_county_years: number
  years: [number, number]
  mae_pct: number
  mae_normal_year_pct: number
  skill_pct: number
  reliable: boolean
  signal: 'strong' | 'weak' | 'none'
  intervals_pct: Record<string, [number, number]>
}

export type CountyForecast = {
  forecast: null | {
    year: number
    median_kg_ha: number
    long_median_kg_ha: number
    yield_kg_ha: number
    intervals_kg_ha: Record<string, [number, number]>
    low_kg_ha: number
    high_kg_ha: number
    anomaly_pct: number
    contributions: { key: string; label: string; value: number; unit: string; effect_pct: number }[]
    model: ForecastModel
    supply: null | {
      area_ha: number; area_year: number; production_t: number; intervals_t: Record<string, [number, number]>
      low_t: number; high_t: number; normal_t: number; vs_normal_pct: number; latest_t: number | null; latest_year: number | null
    }
  }
  history: { year: number; actual_kg_ha: number | null; predicted_kg_ha: number | null; low_kg_ha: number | null; high_kg_ha: number | null }[]
}

export type Forecast = {
  crop: string
  proxy: string | null
  model: ForecastModel | null
  coverage_80_pct: number | null
  counties: Record<string, CountyForecast>
  region: null | { year: number; counties: string[]; production_t: number; low_t: number; high_t: number; normal_t: number; latest_t: number; signal: 'strong' | 'weak' }
  method: string[]
  limits: string[]
  sources: string[]
}

// ---------- assistant ----------
export type AssistantAction =
  | { type: 'select_area'; unit_id: string }
  | { type: 'open_section'; section: string }
  | { type: 'color_map'; kind: 'indicator' | 'agro' | 'soil' | 'cropshare'; key: string; year?: string | null }
  | { type: 'set_procurement_crop'; crop: string; metric?: 'availability' | 'quality' | 'impact' | null }

export type AssistantChoice = { id: string; name: string; kind: string; county_name: string }

export type ChatResponse = {
  reply: string
  sig: string
  mode: 'rule' | 'llm' | 'refused' | 'limited' | 'offline'
  actions: AssistantAction[]
  choices: AssistantChoice[]
  sources: string[]
  unverified: string[]
}

export type ChatTurn = { role: 'user' | 'assistant'; text: string; sig?: string }

export type ChatContext = { unit_id: string | null; role: 'farmer' | 'procurement'; section: string; lang: 'en' | 'ro' }

export type AssistantStatus = { llm: boolean; max_chars: number; limits: { per_minute: number; per_day: number }; llm_available_today: boolean }

// ---------- drawn fields ----------
export type FieldPolygon = import('geojson').Polygon
export type FieldCommune = { id: string; name: string; county: string; county_name: string; share_pct: number }
export type FieldMeasure = {
  area_ha: number
  perimeter_m: number
  centroid: [number, number]
  bbox: [number, number, number, number]
  commune: FieldCommune | null
  geometry: FieldPolygon
  warnings?: string[]
}
export type SavedField = { id: number; name: string; area_ha: number | null; commune_id: string | null; geometry: FieldPolygon }

export type CellEntry = {
  cell: string
  center: [number, number]
  geometry: import('geojson').Polygon
  cell_area_km2: number
  share_of_field_pct: number
  field_share_of_cell_pct: number | null
  status: 'ok' | 'no_data'
  yearly?: Record<string, number>
  latest_month?: { month: string; value: number } | null
  last_12_months?: { month: string; value: number | null }[]
  missing_months?: number
}
export type CellDataset = {
  dataset: string
  label: string
  unit: string
  aggregation: 'sum' | 'mean'
  about: string
  source: string
  resolution: string
  period: { start: string; end: string }
  last_day?: string
  kind: 'surrounding_area_estimate'
  note: string
  cells: CellEntry[]
}
export type SoilContext = {
  status: 'ok' | 'no_data' | 'unavailable'
  source: string
  kind: 'model_pixels'
  resolution?: string
  note: string
  properties: Record<string, { label: string; unit: string }>
  values?: Record<string, { mean: number; min: number; max: number } | null>
  pixels?: { count: number; selection: string; pixel_size_m: [number, number]; pixel_area_ha: number; pixels: import('geojson').FeatureCollection } | null
}
export type SmapContext = {
  dataset: string
  status: 'ok' | 'no_data'
  label?: string
  unit?: string
  source: string
  resolution: string
  kind?: 'commune_average'
  commune?: string
  latest_month?: { month: string; value: number } | null
  last_12_months?: { month: string; value: number | null }[]
  note: string
}
export type FieldContextResp = { field: FieldMeasure; cells: CellDataset[]; soil: SoilContext; smap: SmapContext | null }

export type ObsStatus = 'clear' | 'partly_cloudy' | 'suspect' | 'cloudy' | 'no_data' | 'error'
export type VegObs = {
  date: string
  datetime: string
  source: 'hls' | 's2'
  sensor: string
  tile: string
  item_id: string
  scene_cloud_pct: number | null
  status: ObsStatus
  pixel_size_m: number
  pixels_in_field: number | null
  pixel_selection?: string
  valid_pixels?: number
  valid_pct: number | null
  ndvi: { mean: number; median: number; p10: number; p90: number } | null
  note?: string
}
export type VegPeak = { year: number; window: string; value: number | null; n_used: number; n_read: number; dates: string[]; status: string }
export type VegSource = {
  status: 'ok' | 'error' | 'unavailable'
  label?: string
  short?: string
  resolution_m?: number
  cloud_mask?: string
  nasa?: boolean
  note?: string
  observations?: VegObs[]
  counts?: Partial<Record<ObsStatus, number>>
  latest_clear?: (VegObs & { overlay: { image: string; corners: [number, number][]; pixel_size_m: number; date: string; sensor: string; pixels_in_field: number } | null }) | null
  peaks?: VegPeak[]
}
export type VegResult = {
  field: Omit<FieldMeasure, 'geometry'>
  fetched_at: string
  season: { year: number; start: string; end: string }
  index: string
  status_rules: Record<string, string>
  pending: string[]
  sources: Partial<Record<'hls' | 's2', VegSource>>
}
export type VegJob = { job_id: string; status: 'queued' | 'running' | 'done' | 'error'; stage: string; progress: { done: number; total: number }; error: string | null; result: VegResult | null }
