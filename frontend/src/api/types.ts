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
