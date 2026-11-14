# Datasets: Field Shift / SPACE2FEED (NASA Space Apps 2026, Alba Iulia)

Reference for every raw dataset in `backend/.cache/raw/`: where it is, its exact file structure, units and quirks. Read it before writing code that loads data.

Data paths below (`data/...`) are relative to `backend/.cache/raw/`, which is gitignored and local only (about 1.2 GB; ask the user for a copy if it is missing). Processed, compact JSON for the app goes in `backend/data/` (see `CLAUDE.md`).

## Common facts

- **Area of interest (AOI):** Alba county plus its seven neighbours: Arad, Bihor, Cluj, Hunedoara, Mureș, Sibiu, Vâlcea.
  - The clipping box is about 20.6–25.4°E, 44.4–47.7°N. The exact union of the 8 counties spans 20.705–25.318°E, 44.490–47.600°N.
  - Raster products are clipped to that box or slightly larger. Mask them with `data/boundaries/aoi_union.geojson` or the per-county polygons when you need exact borders.
- **Period:** 2015–2025. Exceptions are listed under each dataset.
- **CRS:** EPSG:4326 (lon/lat) everywhere except EUCROPMAP, which is EPSG:3035 (LAEA Europe, metres).
- **Romanian names are ASCII and upper-case in the boundaries:** `ALBA`, `MURES`, `VALCEA`. INS uses title case without diacritics: `Alba`, `Mures`, `Valcea`.
- **Status markers:** ✅ = complete. 🧪 = only a sample is here so far; the full set is still processing on NASA's side (see "Pending downloads").
- **Python environment:** Python 3.12 via uv, e.g. `cd backend && uv run --with-requirements scripts/download/requirements.txt python -I scripts/download/<script>.py .cache/raw ...`.
  - Tested versions: rasterio 1.5.2, xarray 2026.9.0, shapely 2.2.0, numpy 2.5.4, pandas 3.1.1. netCDF4, h5netcdf and h5py are also needed.
  - Downloaded files are untrusted input. Run Python with `-I` and never execute anything from inside `data/`.

## NASA data source rule (from the challenge)

- At least one NASA Earth-observation dataset must be used for real in the solution, and every source must be credited on the project page and in the pitch.
- NASA datasets here: **POWER, GPM IMERG, GLDAS, FIRMS, NEX-GDDP-CMIP6, MODIS (MOD13Q1, MOD16A2GF, MOD11A2), SMAP (SPL3SMP_E, SPL4SMGP), ECOSTRESS, HLS, SRTM.**
- Non-NASA supplements: SoilGrids (ISRIC), EUCROPMAP (JRC), INS TEMPO (Romanian statistics institute), geoBoundaries.
- Never use the NASA logo ("meatball") and never imply NASA endorsement.

---

## 1. Boundaries ✅ (`data/boundaries/`)

Source: geoBoundaries gbOpen (CC BY 4.0), release `9469f09`. API metadata is in `meta_ADM*.json`.

These raw files were used only to clip the downloads. **The app's own boundary layers are `backend/data/geo/` (see `CLAUDE.md`)**: 662 communes with `id`s like `AB-0012` and county `code`s like `AB`. Aggregate indicators to those units, not to the 677 raw communes below.

| File | Features | Properties |
|---|---|---|
| `ROU_ADM0.geojson` | 1 | Romania outline |
| `ROU_ADM1.geojson` (32 MB) | 42 counties | `shapeName` (e.g. `ALBA`), `shapeISO` (`RO-AB`), `shapeID`, `shapeGroup`, `shapeType` |
| `ROU_ADM2.geojson` (195 MB) | 3,235 communes, towns and cities | same; `shapeISO` is empty |
| `aoi_counties.geojson` | 8 AOI counties, simplified to 0.001° | same as ADM1 |
| `aoi_communes.geojson` | 677 AOI communes, simplified to 0.0005° | ADM2 props + `county` (e.g. `ALBA`), assigned by representative point |
| `aoi_union.geojson` | 1 | `name: Alba+neighbours`; dissolved outline of the 8 counties |

Use the `aoi_*` files in the app; the full ADM files are large.

## 2. NASA POWER daily ✅ (`data/nasa_power/daily_grid/`)

- **Files:** 56 CSVs named `power_daily_{lat:.3f}_{lon:.3f}.csv`, on POWER's native MERRA-2 grid.
  - lat 44.5–47.5, step 0.5 (7 values); lon 20.625–25.0, step 0.625 (8 values).
  - Each value is the average over a 0.5° × 0.625° cell, so this data is **regional, not per field**.
- **Period:** 2015-01-01 to 2025-12-31, daily, 4,018 rows per file. Community `AG`.
- **Format:**
  - A text header runs from `-BEGIN HEADER-` to `-END HEADER-` (about 27 lines). Skip it: `pd.read_csv(f, skiprows=<index of -END HEADER- line>+1)`, or find the line that starts with `YEAR,DOY`.
  - Columns are `YEAR, DOY` followed by the parameters. Build the date from `YEAR` + `DOY`.
  - Missing value is `-999`.

| Column | Meaning | Unit |
|---|---|---|
| `T2M`, `T2M_MAX`, `T2M_MIN`, `T2M_RANGE` | air temperature at 2 m: mean, max, min, daily range | °C |
| `T2MDEW` | dew/frost point | °C |
| `TS` | earth skin temperature | °C |
| `RH2M` | relative humidity | % |
| `QV2M` | specific humidity | g/kg |
| `PRECTOTCORR` | precipitation, bias-corrected | mm/day |
| `ALLSKY_SFC_SW_DWN`, `CLRSKY_SFC_SW_DWN` | solar radiation (all-sky, clear-sky) | MJ/m²/day |
| `ALLSKY_SFC_PAR_TOT` | photosynthetically active radiation | MJ/m²/day |
| `WS2M` | wind speed at 2 m | m/s |
| `PS` | surface pressure | kPa |
| `GWETTOP`, `GWETROOT`, `GWETPROF` | soil wetness: surface, root zone, whole profile | 0–1 fraction |
| `EVPTRNS` | evapotranspiration energy flux | MJ/m²/day; divide by 2.45 for mm/day |

**Useful derived indicators:**
- heat days: `T2M_MAX ≥ 32`, or `≥ 35` during maize flowering (July–August)
- growing degree days: base 10 °C for maize, 0–5 °C for wheat
- frost days: `T2M_MIN < 0`
- rainfall during sensitive phases: wheat flowering (late May–June), harvest windows

## 3. GPM IMERG precipitation ✅ (`data/precipitation/`)

Source: GPM IMERG Final Run V07B from GES DISC, clipped on NASA's cloud OPeNDAP server. Grid is 0.1°, 50 lon × 35 lat, lon 20.55–25.45, lat 44.35–47.75 (cell centres).

| Folder | Files | Period | Variables | Unit |
|---|---|---|---|---|
| `gpm_imerg_daily/{YYYY}/IMERG_daily_{YYYYMMDD}_AOI.nc4` | 3,926 | 2015-01-01 to **2025-09-30** | `precipitation`, `randomError` | **mm/day** |
| `gpm_imerg_monthly/IMERG_monthly_{YYYYMM}_AOI.nc4` | 129 | 2015-01 to **2025-09** | `precipitation`, in HDF5 group **`Grid`** | **mm/hr**; multiply by 24 × days in the month for the monthly total |

- **The archive ends at 2025-09:** NASA's Final archive currently stops on 2025-09-30, so October–December 2025 don't exist yet. For those months, use POWER `PRECTOTCORR`, or IMERG Late (not downloaded).
- **Dimension order is `(time, lon, lat)`, not `(time, lat, lon)`:** transpose before plotting, e.g. `ds.precipitation.transpose('time','lat','lon')`.
- **Opening the files:**
  - daily: `xr.open_mfdataset('data/precipitation/gpm_imerg_daily/*/*.nc4', combine='by_coords')`
  - monthly: `xr.open_dataset(f, group='Grid')`. Without `group='Grid'` you get an empty dataset.

## 4. GLDAS Noah land model, monthly ✅ (`data/land_model/gldas_noah025_monthly/`)

- **Product and files:** GLDAS_NOAH025_M v2.1, clipped via cloud OPeNDAP. 132 files named `GLDAS_NOAH025_M_{YYYYMM}_AOI.nc4`, covering 2015-01 to 2025-12.
- **Grid:** 0.25°, dims `(time, lat, lon)` = (1, 14, 20). lat 44.375–47.625, lon 20.625–25.375.

| Variable | Meaning | Unit |
|---|---|---|
| `SoilMoi0_10cm_inst`, `SoilMoi10_40cm_inst`, `SoilMoi40_100cm_inst` | soil moisture by layer | kg/m², which equals mm of water in the layer; divide by layer thickness in mm for volumetric fraction |
| `RootMoist_inst` | root-zone soil moisture | kg/m² |
| `Evap_tavg` | evapotranspiration | kg/m²/s; × 86,400 for mm/day |
| `Rainf_f_tavg` | rainfall | kg/m²/s; × 86,400 for mm/day |
| `PotEvap_tavg` | potential evaporation | W/m² |
| `ESoil_tavg`, `ECanop_tavg`, `Tveg_tavg` | soil evaporation, canopy evaporation, transpiration | W/m² |
| `Tair_f_inst` | air temperature | **K** (−273.15 for °C) |
| `Qair_f_inst` | specific humidity | kg/kg |
| `SWdown_f_tavg` | downward shortwave radiation | W/m² |

Use GLDAS as a stand-in for soil moisture until the SMAP full set arrives, and as a longer, gap-free soil-moisture series.

## 5. NASA FIRMS active fires ✅ (`data/firms/romania_country_yearly/`)

- **Files:** 22 CSVs, `modis_{YYYY}_Romania.csv` and `viirs-snpp_{YYYY}_Romania.csv` for 2015–2025, about 184k rows in all. This is the **whole of Romania**; filter to the AOI with `aoi_union.geojson`.
- **MODIS columns:** `latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type`. `confidence` is 0–100.
- **VIIRS columns:** the same, except `bright_ti4` / `bright_ti5` replace `brightness` / `bright_t31`. `confidence` is `l`, `n` or `h` (low, nominal, high).
- **Shared fields:**
  - `acq_time` is UTC as HHMM.
  - `frp` is fire radiative power in MW.
  - `type`: 0 = presumed vegetation fire, 2 = other static land source, 3 = offshore. Keep `type == 0` for agricultural burning.
- **Agricultural burning signal:** detections on cropland pixels (join with EUCROPMAP), clustered after harvest (July–September) and in early spring (March–April).

## 6. NEX-GDDP-CMIP6 climate scenarios ✅ (`data/climate_scenarios/nex_gddp_cmip6/`)

- **Source:** NASA NEX-GDDP-CMIP6, clipped via the NCCS THREDDS server. Bias-corrected, downscaled daily data on a 0.25° grid.
- **Layout:** `{MODEL}/{SCENARIO}/{VAR}/{VAR}_{MODEL}_{SCENARIO}_{YYYY}_AOI.nc`. 1,380 files: one per model, scenario, variable and year.
  - Models (all `r1i1p1f1`): `GFDL-ESM4`, `MPI-ESM1-2-HR`, `EC-Earth3`.
  - Scenarios: `historical` 1995–2014; `ssp245` and `ssp585` 2025–2060.
- **Dims and calendar:** `(time, lat, lon)` = (365 or 366, 15, 21); lat 44.375–47.875, lon 20.625–25.625.
  - Calendars depend on the model. GFDL-ESM4 uses `365_day` (no leap days; xarray decodes it as cftime objects). EC-Earth3 uses `proleptic_gregorian` (leap years have 366 days). Normalize before combining models, e.g. group by year or month.

| Var | Meaning | Unit |
|---|---|---|
| `tas`, `tasmax`, `tasmin` | air temperature: mean, max, min | **K** |
| `pr` | precipitation | **kg/m²/s**; × 86,400 for mm/day |
| `hurs` | relative humidity | % |

- **Use:** compare 2041–2060 against the 1995–2014 baseline (a delta method), e.g. change in heat days during maize flowering.
- **Uncertainty:** show the spread across the 3 models as an uncertainty band.

## 7. SoilGrids 2.0 ✅ (`data/soil/soilgrids/`)

- **Source:** ISRIC SoilGrids (CC BY 4.0), via WCS.
- **Files:** 40 GeoTIFFs named `{prop}_{depth}_mean.tif`. Depths are `0-5cm`, `5-15cm`, `15-30cm`, `30-60cm`.
- **Grid:** EPSG:4326, about 0.00226° × 0.00239° (≈250 m), 2,123 × 1,381 px. Bounds 20.6–25.4°E, 44.4–47.7°N. `int16`.
- **No data:** 0 means no data, about 3.4% of pixels (water and urban); the file has no nodata tag set. Mask with `a == 0`.
- **All values are scaled integers.** Divide as shown to get the conventional unit.

| prop | Meaning | Stored unit | Divide by | Conventional unit | Typical AOI value (0–5 cm median) |
|---|---|---|---|---|---|
| `soc` | soil organic carbon | dg/kg | 10 | g/kg | 471 → 47 g/kg |
| `phh2o` | pH in water | pH × 10 | 10 | pH | 62 → 6.2 (5th–95th percentile: 5.3–7.2) |
| `clay`, `sand`, `silt` | texture fractions | g/kg | 10 | % | clay 357 → 35.7% |
| `nitrogen` | total nitrogen | cg/kg | 100 | g/kg | 559 → 5.6 g/kg |
| `bdod` | bulk density | cg/cm³ | 100 | g/cm³ | 130 → 1.30 |
| `cec` | cation exchange capacity | mmol(c)/kg | 10 | cmol(c)/kg | 278 → 27.8 |
| `ocd` | organic carbon density | hg/m³ | 10 | kg/m³ | 424 → 42.4 |
| `cfvo` | coarse fragments | cm³/dm³ | 10 | vol % | 164 → 16.4% |

Texture class: apply the USDA texture triangle to clay/sand/silt in %.

## 8. EUCROPMAP crop-type maps ✅ (`data/crops/eucropmap/`)

- **Source:** JRC EUCROPMAP (CC BY 4.0, "© European Union"; see `2018_copyright.txt`), clipped remotely from the EU-wide files.
- **Files:** `EUCROPMAP_2018_AOI.tif` (int16) and `EUCROPMAP_2022_AOI.tif` (int32).
  - CRS **EPSG:3035**, 10 m pixels, 42,651 × 42,657 px. Bounds in metres: x 5,113,970–5,540,480, y 2,425,350–2,851,920.
  - Nodata is 0.
- **Size:** about 1.8 GB each uncompressed. Read with windows, or downsample with `out_shape=` / `rasterio.warp.reproject`. Don't `read()` the full array casually.
- **Legend:** QGIS styles `2018_EuroCropMap.qml` and `2022_EuroCropMap2022.qml` (`<item value=… label=… color=…>`). The codes are the same in both years.

| Code | Class | Code | Class |
|---|---|---|---|
| 100 | artificial | 231 | sunflower |
| 211 | common wheat | 232 | rapeseed / turnip rape |
| 212 | durum wheat | 233 | soya |
| 213 | barley | 240 | dry pulses (peas, chickpeas…) |
| 214 | rye | 250 | fodder crops (cereals + legumes) |
| 215 | oats | 290 | bare arable land |
| 216 | maize | 300 | woodland/shrubland (incl. permanent crops) |
| 217 | rice (2022 only) | 500 | grasslands |
| 218 | triticale (2022 only) | 600 | bare land / lichens / moss |
| 219 | other cereals | 700 | water (2022 only) |
| 221 | potatoes | 800 | wetlands (2022 only) |
| 222 | sugar beet | | |
| 223 | other root crops | | |
| 230 | other non-permanent industrial crops | | |

**Use:**
- crop area per commune or county: reproject the polygons to EPSG:3035 and compute zonal stats
- cropland masks for NDVI and FIRMS
- 2018 → 2022 change as a rough rotation signal; this is only 2 snapshots, not a time series

## 9. INS TEMPO county crop statistics ✅ (`data/crops/ins_tempo/`)

- **Source:** Romanian National Institute of Statistics (INS), TEMPO Online.
- **Tables:**
  - `AGR108A`: cultivated area, hectares
  - `AGR109A`: production, tonnes
  - `AGR110A`: average yield, kg/ha
- **Files:** each table has `{CODE}_AOI_2015plus.csv` (data) and `{CODE}_metadata.json` (dimension option IDs, definitions, notes, last-update date).
- **Filters:** the 8 AOI counties + `TOTAL` (Romania); property form `Total`; years 2015–2025.
- **CSV format:**
  - Comma + space separated; split on `', '`, or use `pd.read_csv(f, sep=', ', engine='python')` and strip whitespace.
  - Header: `Principalele culturi, Forme de proprietate, Macroregiuni  regiuni de dezvoltare si judete, Ani, UM: <unit>, Valoare` (note the double space in the third column name).
  - Example row: `Porumb boabe, Total, Alba, Anul 2015, Kilograme, 4863`.
  - Year is the string `Anul YYYY`.
  - The UM column says `Kilograme` for yield, but the value is **kg/ha**.
  - Values are numeric; crop × county × year combinations with no data are simply missing rows.
- **Hierarchy:** crop names form a hierarchy (`Cereale pentru boabe` > `Grau si secara` > `Grau - total` > `Grau comun`), so totals and sub-items are both present. Don't sum across levels.
- **Crop name mapping** (Romanian → English):

| Romanian | English |
|---|---|
| `Porumb boabe` | grain maize |
| `Grau - total` / `Grau comun` | wheat / common wheat |
| `Orz si orzoaica` / `Orz` | barley (incl. two-row) / barley |
| `Ovaz` | oats |
| `Soia boabe` | soybean |
| `Floarea soarelui` | sunflower |
| `Mazare boabe` | dry peas |
| `Rapita` | rapeseed |
| `In pentru ulei` | oil flax |
| `Leguminoase pentru boabe` | grain legumes (AGR108A) |
| `Lucerna`, `Trifoi` | alfalfa, clover |

Chickpeas are not listed separately.

Example: Alba grain-maize yield fell from 7,411 kg/ha (2018) to 3,168 kg/ha (2025), a useful drought story.

---

## 10. AppEEARS products 🧪 (sample now, full set pending)

These come from NASA AppEEARS (`appeears.earthdatacloud.nasa.gov`) area requests.

- **Full requests:** AOI = `aoi_union` (or Alba only where noted), output projection `geographic` (EPSG:4326).
- **Samples (available first):** `data/_samples/<same sub-path>/`, Alba county only, 2024 (or July 2024 for the high-volume products).
- **Full data:** lands in `data/<sub-path>/` with **the same file naming**, so code written against the samples works unchanged; only the folder differs.
- **Structure:** the section "AppEEARS output structure" below is filled in from the real sample files once they arrive. Treat it as the source of truth over anything else.

| Sub-path | Product | Layers | Full extent / period | Format |
|---|---|---|---|---|
| `vegetation/modis_mod13q1_ndvi_evi` | MOD13Q1.061, 250 m, 16-day | `_250m_16_days_NDVI`, `_250m_16_days_EVI`, `_250m_16_days_pixel_reliability` | AOI, 2015–2025 | GeoTIFF |
| `evapotranspiration/modis_mod16a2gf_et_500m` | MOD16A2GF.061, 500 m, 8-day, gap-filled | `ET_500m`, `PET_500m`, `ET_QC_500m` | AOI, 2015–2025 | GeoTIFF |
| `temperature/modis_mod11a2_lst_1km` | MOD11A2.061, 1 km, 8-day | `LST_Day_1km`, `LST_Night_1km`, `QC_Day` | AOI, 2015–2025 | GeoTIFF |
| `terrain/srtm_gl1_30m` | SRTMGL1_NC.003, 30 m | `SRTMGL1_DEM` (m) | AOI, static | GeoTIFF |
| `soil_moisture/smap_l3_enhanced_9km_daily/{YYYY}` | SPL3SMP_E.006, 9 km, daily | AM `soil_moisture`, PM `soil_moisture_pm`, AM `retrieval_qual_flag` | AOI, 2015-03-31 to 2025, one request per year | NetCDF4 |
| `soil_moisture/smap_l4_9km_3hourly_rootzone/{YYYY}` | SPL4SMGP.008, 9 km, 3-hourly model+assimilation | `sm_surface`, `sm_rootzone`, `sm_rootzone_pctl` | AOI, 2015-03-31 to 2025, one request per year | NetCDF4 |
| `evapotranspiration/ecostress_et_esi_70m_alba/{YYYY}_{1,2}` | ECO_L3T_JET.002 + ECO_L4T_ESI.002, 70 m | `ETdaily`, `ESI`, `cloud` | **Alba only**, Apr–Sep 2018–2025 (1 = Apr–Jun, 2 = Jul–Sep) | GeoTIFF |
| `vegetation/hls_30m_ndvi_alba` | HLSL30_VI / HLSS30_VI .020 + HLSL30 / HLSS30 .020 | `NDVI`, `Fmask` | **Alba only**, Apr–Sep 2023–2025 | GeoTIFF |

**Scaling and QA:**
- MOD13Q1 NDVI/EVI: raw int16 × 0.0001, valid range −2000…10000.
  - `pixel_reliability`: 0 = good, 1 = marginal, 2 = snow/ice, 3 = cloudy, −1 = fill.
- MOD16A2GF ET/PET: × 0.1, giving kg/m² (mm) **per 8-day period** (the last period of the year covers 5–6 days). Fill values are ≥ 32761.
- MOD11A2 LST: × 0.02, giving K. 0 = fill.
- SMAP soil moisture: m³/m³. Fill is −9999.
- HLS NDVI: check whether AppEEARS has scaled it (see the structure section). Fmask is a bit field: bit 1 = cloud, 2 = adjacent cloud, 3 = cloud shadow, 4 = snow, 5 = water.
- SMAP pixels are about 9 km, so a farm parcel has no value of its own. Report SMAP per commune or county, not per field.

### AppEEARS output structure

_To be filled in from `data/_samples/` once the sample requests finish._

---

## Pending downloads and how to resume

- **Scripts:** in `backend/scripts/download/` (each takes the raw data folder as its first argument). AppEEARS task IDs are kept in a local state JSON passed as the second argument.
- **Who downloads what:**
  - `appeears.py <data_dir> <state.json>` submits any missing full requests, polls them and downloads finished bundles.
  - `samples.py <data_dir> <state.json> submit|wait` does the same for the Alba samples.
- **Credentials:** `~/.netrc` (`machine urs.earthdata.nasa.gov`). The account must have the "NASA GESDISC DATA ARCHIVE" app authorized for IMERG and GLDAS. **Never print or commit credentials.**
- **AppEEARS processing:** it runs one request per user at a time, so the full set (43 requests) takes hours. Progress is visible at appeears.earthdatacloud.nasa.gov → Explore.
- **Re-runs:** all download scripts are idempotent and skip files that already exist.

## Not downloaded (and why)

- **US-only sources on the challenge page:** USDA Ag Data Commons, Web Soil Survey, CropScape/CDL, PRISM, SSURGO/STATSGO2, NAIP, NLCD, CoCoRaHS, NWIS, AMS Market News, NASS QuickStats, OpenET, LANDFIRE. None cover Romania.
- **ERA5 and Copernicus Sentinel-2:** need separate accounts. They're covered by POWER + GLDAS and by HLS (which includes Sentinel-2).
- **LUCAS Soil:** needs registration with ESDAC. SoilGrids covers soil.
- **GEDI:** forest structure, not relevant to arable rotations.
- **FAO GAEZ, Eurostat, FAOSTAT:** optional context; fetch on demand if needed.
- **Crop traits** (water need, heat sensitivity, nitrogen fixation, sensitive growth stages): not a dataset. Build a small hand-curated table (extend `backend/data/crops/smart_feed.json`, whose traits are still TODO) with references (FAO-56 crop coefficients, FAO Ecocrop) for the crops of the chosen direction:
  - Direction A: maize, wheat, barley, soybean, sunflower, peas.
  - Direction B: oats, barley, maize, peas, chickpeas, flax, sunflower.
