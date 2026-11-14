# CLAUDE.md — SPACE2FEED (NASA Space Apps 2026, Alba Iulia)

Hackathon project. Read this fully before working. The original brief is a 12-page
Hungarian PDF ("SPACE2FEED · Transavia kihívás", updated 2026-11-13); everything
relevant from it is summarised below — treat this file as the source of truth.

## 1. The challenge

- **Event:** NASA Space Apps Challenge, local event Alba Iulia (Gyulafehérvár), **14–15 Nov 2026**. Times are Romanian time.
- **Official NASA challenge:** **"Field Shift: Adapting Farms with NASA Data"** (project is submitted to this one).
- **Local lens:** SPACE2FEED, by Transavia (Romanian vertically integrated poultry producer, Santimbru, Alba county; grows maize/wheat, hundreds of suppliers, makes pet food since 2025, publishes ESRS sustainability reports since 2024).
- **Our direction: B — SMART FEED (pet food).** Crops: **oats, barley, maize, pea, chickpea, flax, sunflower (oil)**, plus **poultry protein** (its impact depends on the crops in the poultry feed).
  - (Direction A, not ours: livestock feed — maize, wheat, barley, soy, sunflower meal, feed pea.)
- **Core question:** How can we help farmers choose rotations that protect soil and water, and how can a procurement buyer see in time what those choices mean for the raw materials they need?

### Two levels — BOTH needed, NASA core must work on its own
A procurement-only project with no farmer/rotation part risks being judged irrelevant to the NASA challenge. The lens builds **on top of** the core, never replaces it.

**Primary user = farmer.** Wants to: see what happened on their land in past years (water, heat, vegetation); compare 2–3 rotations over 3–4 years; see trade-offs clearly (yield, water, soil, risk); understand *why* something is recommended.

**Secondary user = Transavia procurement team** (for B: team developing pet-food recipes and buying ingredients). Wants to: see availability risk per area and crop; anticipate weather-related quality issues; compare environmental impact of sources; know where each ingredient comes from and how reliable the estimate is.

### Requirements (numbered as in the brief)
NASA core (mandatory):
1. **Analysis area:** a parcel drawn on a map **or** a Romanian administrative unit. Recommended: **Alba county and neighbours**.
2. **≥ 3 indicators from NASA data, multi-year** (e.g. vegetation, soil moisture, precipitation, temperature).
3. **Soil data for the area:** organic carbon, texture, pH.
4. **Crop characteristics:** water need, heat sensitivity, soil effect (e.g. legumes fix nitrogen).
5. **Farmer priorities, set by the user:** yield, water, soil health, risk.
6. **≥ 2 rotation strategies compared over 3–4 years, with explained scores.**

Transavia lens:
7. **Procurement view:** field results aggregated per area for the chosen direction's ingredient crops.
8. **Three dimensions:** availability (production risk), quality (weather risks in crop-critical periods), environmental impact (water, soil, estimated emissions).
9. **Procurement strategy recommendation:** e.g. buying spread across areas, alternative ingredients, contracts with farmers using better rotations.
10. **Transparency:** every result shows data used, time period, assumptions, confidence level.
11. **AI with a clear role:** forecasting, risk classification, optimisation, or an assistant explaining results. Must state what the model does and **where it fails**.

Optional bonus: climate scenarios for coming decades (NASA **NEX-GDDP-CMIP6**); **Romanian-language, phone-first UI**; flagging agricultural burning in the region (NASA **FIRMS**); impact estimate with explicit assumptions (e.g. what changes if 1/4 of suppliers adopt legume rotations).

**Minimum to show in the pitch (demo or concept):** (1) select an area on the map, (2) show ≥ 3 NASA indicators over **≥ 5 years**, (3) compare two rotations and explain the scores, (4) show what the result means for procurement of the ingredient crop. Pitch part 1 always presents the farmer tool.

Direction-B starter questions: Which locally grown plant ingredients give stable supply and lower impact than imports? How to show a recipe's environmental footprint transparently, starting from the field? How does a recipe's sourcing risk change if one ingredient is swapped for another?

### Measuring the three dimensions (guidance from brief)
- **Availability:** how much can be produced in the area and how reliably — peak-season vegetation vs. previous years, soil-moisture deficit in critical months, crop areas per crop (EUCROPMAP, INS).
- **Quality:** weather risk in sensitive phases — heat + drought at **maize flowering** (aflatoxin risk), high humidity at **wheat flowering** (fusarium/mycotoxin), rain at harvest.
- **Environmental impact:** water (evapotranspiration, water deficit), soil (legume rotations, winter cover, organic carbon), emissions estimated with public factors, burning flagged by FIRMS.

Example from the brief (fictional users): farmer Ana, 120 ha near Aiud, priorities water + soil, compares current maize–wheat–maize with a rotation including soy + sunflower, sees heatwave days during maize flowering. Buyer Mihai sees the same data aggregated over ~40 communes: maize risk this year, potential soy output in two years, reliability of estimates.

### Rules (hard constraints)
- Use **≥ 1 NASA data source genuinely in the solution**, and **cite every source** on the project page and in the pitch. Other open data welcome as supplements.
- **Public data only; never invent data.** Project page and code are public — no confidential/private data.
- **No NASA "meatball" or any NASA logo**, nothing implying NASA endorses the project or partners. May say "built at the NASA Space Apps Challenge".
- Generative AI allowed with a clear, declared role; follow Space Apps AI rules on the submission form; verify model output.
- Show uncertainty (intervals beat point estimates). Correlation ≠ causation: explain *why* an indicator changes a risk.
- Resolution caveat: one SMAP pixel is kilometres wide — a few-hectare parcel has no own value. Optical imagery has cloud gaps: use composites or combine sources.
- Organisers' advice: start small — one county, 2–3 crops, 3 indicators; expand only when it works.

### Deadlines & judging
- Sat 14 Nov: 08:30 check-in, 09:30 opening, building from 11:00.
- **Sun 15 Nov 15:00** local pitch form (files/links). **15:30** pitches (e.g. 5 min + 3 min Q&A; usually in English). **18:50** mandatory submission on the NASA Space Apps site (Field Shift): summary, demo, project/code link, NASA data + other sources, AI-use info. ~19:00 awards.
- Five criteria, 20 % each: **Impact, Creativity, Validity (scientific/technical soundness), Relevance (to challenge + proper NASA data use), Presentation.** Tie-break: Impact → Validity → Creativity.
- Prizes: 3000 / 2000 / 1000 EUR. ≥ 2/3 of team must be present at judging.

### Data sources named in the brief
NASA (priority; official list is on the Field Shift challenge page):
| What | Source | Notes |
|---|---|---|
| Vegetation (NDVI, EVI) | **HLS** (Landsat+Sentinel-2) 30 m; **MODIS MOD13Q1** 250 m, 16-day | |
| Soil moisture | **SMAP L3/L4** | surface 9–36 km; root zone (0–1 m) 9 km |
| Precipitation | **GPM IMERG** | 0.1°, every 30 min |
| Temperature, radiation, daily precip | **NASA POWER** | daily since 1981, API, **no account needed** — easiest start |
| Water stress, ET | **ECOSTRESS** | 70 m, from ISS |
| Agricultural burning | **FIRMS** (MODIS, VIIRS) | near-real-time active fires |
| Climate scenarios | **NEX-GDDP-CMIP6** | daily, 0.25° |
| Tools | Earthdata Search, **AppEEARS** (time series for points/polygons: MODIS, SMAP, ECOSTRESS…), Worldview, NASA Harvest / GEOGLAM | most downloads need a free **Earthdata login** (urs.earthdata.nasa.gov) |

Other open data: Copernicus Data Space (Sentinel-1/2), **EUCROPMAP 2018** (JRC, 10 m, 19 crop types), **SoilGrids** (ISRIC, 250 m — use for org. carbon/texture/pH), LUCAS Soil (JRC/ESDAC, registration), **INS TEMPO** (production per county), Eurostat, FAOSTAT.

## 2. Architecture & decisions (agreed with the user — don't change without asking)

- **Frontend:** React 19 + TypeScript 7 + Vite 8 (pnpm), **MapLibre GL 6** (free vector map, no API key). Not Google Maps.
- **Backend:** Python **3.12** (uv-managed; system Python is 3.9 — always use `uv run`), **FastAPI**, uvicorn, orjson, pydantic-settings, SQLModel.
- **SQLite** (`backend/app.db`, gitignored) is **only for app state**: farms, fields (drawn parcels), farmer priorities.
- **NASA / geo / reference data are plain JSON files** in `backend/data/`, **never in the DB** (speed). Loaded once into memory by `app/json_store.py` (mtime hot-reload in dev).
- Map shows **only Romania** (outside masked), counties + 8 development regions + communes for Alba & neighbours.

### Layout
```
backend/
  app/main.py            FastAPI app; GZip, CORS (localhost:5173), ORJSONResponse; routers under /api
  app/config.py          Settings (env prefix S2F_): data_dir, db_url, cors_origins, json_hot_reload
  app/db.py, models.py   SQLModel engine; tables Farm, Field_ ("field"), FarmerPriorities (yield/water/soil/risk weights)
  app/json_store.py      store.get(rel) -> parsed, store.raw(rel) -> bytes, store.list(subdir)
  app/routers/health.py  GET /api/health
  app/routers/geo.py     GET /api/geo, /api/geo/{counties|regions|communes|outline|mask|labels}
  app/routers/nasa.py    GET /api/nasa, /api/nasa/{dataset}?unit=<id>, /api/nasa/crops/{direction}
  data/geo/*.geojson.json   generated boundary layers (committed)
  data/nasa/             NASA datasets as JSON — schema in data/nasa/README.md (currently empty)
  data/crops/smart_feed.json  direction-B crop list (ids + RO/EN/HU names; traits still TODO)
  scripts/build_boundaries.py  regenerates data/geo (uv dependency group "scripts": geopandas, shapely, requests)
  .cache/                downloaded raw sources (gitignored)
frontend/
  src/App.tsx            header + map + side panel (selected area, region legend)
  src/api/client.ts      getJson(), getGeoLayer() — base "/api" (Vite proxies to :8000)
  src/map/RomaniaMap.tsx MapLibre map; emits AreaSelection (county | commune) via onSelect; Alba preselected
  src/map/style.ts       basemap URL, bounds, layer specs (lowLayers under roads, topLayers incl. mask)
  src/map/regionColors.ts REGION_COLORS, COUNTY_REGION, countyColor(), countyColorExpression
  vite.config.ts         /api proxy; optimizeDeps.exclude maplibre-gl (its ESM worker breaks if pre-bundled)
.claude/launch.json      preview configs "backend" (:8000) and "frontend" (:5173)
```

### Run
```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000   # docs at /docs
cd frontend && pnpm install && pnpm dev                                      # http://localhost:5173
cd backend && uv run --group scripts python scripts/build_boundaries.py      # rebuild geo layers
cd frontend && pnpm build                                                    # tsc -b + vite build (must pass)
```

## 3. Data we have

### Geo layers (`backend/data/geo/`, ~9 MB raw, gzip over API)
| File | Content | Key properties |
|---|---|---|
| `counties` | 42 (41 județe + București) | `code` (AB, CJ, B…), `name` (with diacritics), `region`, `nuts2` |
| `regions` | 8 development regions (NUTS-2) | `name`, `nuts2` |
| `communes` | 662 UATs in **AB, AR, BH, CJ, HD, MS, SB, VL** | `id` (e.g. `AB-0012`), `name`, `county`, `county_name`, `region` |
| `outline` | Romania polygon | |
| `mask` | world minus Romania | used to hide everything outside |
| `labels` | label points (polylabel) | `kind` region/county/commune, `name`, `code` |

- Source: **geoBoundaries gbOpen ROU ADM2** (ANCPI cadastre, **2016**, CC BY 4.0) → 3187 UATs (3181 + 6 Bucharest sectors). Counties/regions are **dissolved from communes**, so all levels share exact edges. ADM1 (World Bank 2017) only used to assign communes to counties.
- Coverage-simplified ~0.0003° (~25–30 m), 5-decimal coords.
- Commune names with diacritics from **OSM admin_level=8** (Overpass, fetched 2026-11-14): 3039/3187 matched; rest title-cased fallback. (RO in OSM: admin_level 4 = județ, 8 = UAT.)
- **Commune `id`s are generated by sort order, not SIRUTA codes** — they are stable only while the build inputs are unchanged. If you need joins with INS/other data, add SIRUTA (OSM `ref:siruta`) to the pipeline.
- Basemap: OpenFreeMap "liberty" (OSM planet build 2026-11-01). Hillshade: AWS terrarium DEM tiles. Attributions are on the map and in README — keep them.

### NASA data — format (`backend/data/nasa/<dataset>.json`)
```json
{ "source": "NASA POWER (power.larc.nasa.gov)", "variable": "T2M_MAX", "unit": "°C",
  "period": {"start": "2019-01-01", "end": "2025-12-31", "step": "month"},
  "units": { "AB": {"2019-01": 2.1}, "AB-0012": {"2019-01": 1.8} } }
```
`units` keys = county `code` or commune `id`. **Always fill `source`** (transparency requirement). No NASA datasets are downloaded yet — that's the next step; NASA POWER needs no account, others need Earthdata login.

## 4. Conventions
- Romanian names always with comma-below **ș ț** (not cedilla ş ţ), plus ă â î.
- Never fabricate data or numbers; if something is estimated, mark it and show assumptions + confidence.
- Large/raw downloads go to `backend/.cache/` (gitignored); only processed, compact JSON goes in `backend/data/`.
- Keep the map Romania-only and keep the boundary hierarchy consistent (generate from the same source).
- Commit only when the user asks; remote is `origin` (GitHub), branch `main`.
