# Dani's downloaded dataset

Purpose: the raw data (about 12 GB) is not in git (`data/` is gitignored). This file and `data_manifest_dani.tsv` describe what Dani has, so it can be compared against the other person's data and any missing files re-downloaded.

- **Snapshot:** 2026-11-14 about 12:05 local. SMAP was still downloading, so re-run `python3 -I scripts/manifest.py` for a fresh manifest.
- **Region:** Alba Iulia, Romania. Box 45.6-46.5 N, 23.0-24.2 E (centre 46.07 N, 23.57 E).
- **Target period:** 2021-11-01 to 2026-10-31, unless a source ends earlier.
- **Full file list:** `data_manifest_dani.tsv` (columns `path`, `size_bytes`; READMEs and `.part` files excluded). Each `data/<folder>/README.md` has variable-level detail.

## How to compare

1. Run `python3 -I scripts/manifest.py other.tsv` in your own repo, which writes your own file list.
2. Compare by **file name** per folder. Check `size_bytes` too, since a size mismatch means a truncated or re-processed file.
3. For SMAP, compare the **date** in the name (`..._YYYYMMDD_...`), not the `_<n>_` index, because the index depends on the order Harmony returned files and can differ between runs.
4. Re-download only what is missing, using the script and source listed for that dataset.

All NASA Earthdata downloads need a token saved in `~/.earthdata_token` (never commit it). POWER, SoilGrids and WorldCover need no login.

## Inventory

| Folder | Files | Size | Coverage | Source | Script |
|---|---|---|---|---|---|
| `power` | 9 | 2.6 MB | daily 2021-11-01 to 2026-10-31 | NASA POWER API | `scripts/power.py` |
| `imerg_monthly` | 47 | 868 MB | monthly 2021-11 to 2025-09 | GES DISC via CMR | `scripts/imerg.py` |
| `gldas_monthly` | 57 | 1.4 GB | monthly 2021-11 to 2026-07 | GES DISC via CMR | `scripts/soil_landcover_gldas.py` |
| `smap` | 741 + 1 stray | 1.0 GB so far | daily 2021-11-01 onward, **in progress** | NSIDC via Harmony | `scripts/smap_all.py` |
| `grace_tws` | 1 | 46 MB | monthly 2002-04 to 2026-09 (global) | PO.DAAC via CMR | `scripts/extra.py` |
| `modis_ndvi` | 60 | 1.1 GB | monthly 2021-11 to 2026-10 | LP DAAC via CMR | `scripts/srtm_modis.py` |
| `modis_et` | 192 | 4.5 GB | 8-day 2021-11-01 to 2025-12-27 | LP DAAC via CMR | `scripts/extra.py` |
| `modis_lst` | 229 | 1.8 GB | 8-day 2021-11-01 to 2026-10-24 | LP DAAC via CMR | `scripts/extra.py` |
| `soilgrids` | 40 | 6.5 MB | static | ISRIC WCS | `scripts/soil_landcover_gldas.py` |
| `srtm` | 6 | 75 MB | static (2000) | LP DAAC via CMR | `scripts/srtm_modis.py` |
| `worldcover` | 2 | 161 MB | static (2021) | ESA S3 bucket | `scripts/soil_landcover_gldas.py` |

Sizes are rounded and SMAP is still growing; use the manifest for exact values.

## Per-dataset detail

### power: NASA POWER daily agro-climate
- Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`, community `AG`, JSON.
- Parameters: `T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M, ALLSKY_SFC_SW_DWN, GWETROOT, GWETTOP, EVLAND`.
- Files: one per point, `power_<lat>_<lon>.json`, for lat in {45.7, 46.07, 46.4} and lon in {23.1, 23.57, 24.1}. That is 9 files, each with 1826 daily values.

### imerg_monthly: GPM IMERG monthly precipitation
- CMR short name `GPM_3IMERGM`, version `07`. HDF5, global 0.1° grid (clip when reading).
- Files named `3B-MO.MS.MRG.3IMERG.<YYYYMMDD>-S000000-E235959.<MM>.V07B.HDF5`, one per month. Newest available month is 2025-09, so there are no files after that.

### gldas_monthly: GLDAS Noah land model
- CMR short name `GLDAS_NOAH025_M`, version `2.1`. NetCDF4, global 0.25° grid.
- Files named `GLDAS_NOAH025_M.A<YYYYMM>.021.nc4`. Newest available month is 2026-07.

### smap: SMAP L3 daily soil moisture, spatially subset
- Product `SPL3SMP_E` v006, NSIDC collection `C2938664763-NSIDC_CPRD`, requested through the Harmony coverages API with `lat(45.6:46.5)`, `lon(23.0:24.2)` and one job per calendar month.
- Files named `<YYYY-MM>_<n>_SMAP_L3_SM_P_E_<YYYYMMDD>_R19240_001_subsetted.nc4`. About 1.4 MB each.
- **Still downloading.** Months done so far: 2021-11 to 2023-11 (last file date 2023-12-01). The script covers through 2026-10.
- **Gap in the source data (probably):** 2022-08 has only 6 files (Aug 1-6) and 2022-09 has 11 (Sep 20 to Oct 1, plus one Oct 1). There are no daily files from 2022-08-07 to 2022-09-19. Harmony reported the jobs as successful, so this is most likely a gap in SMAP itself, not failed downloads.
- Stray file: `test_7_SMAP_L3_SM_P_E_20211108_R19240_001_subsetted.nc4` is a leftover from a test run. Ignore it.

### grace_tws: GRACE / GRACE-FO water storage
- CMR short name `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` (JPL mascon, CRI filtered). One global file, no region subset.
- File: `GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc`. It has a known data gap between GRACE and GRACE-FO (mid-2017 to mid-2018).

### modis_ndvi: MOD13A3 monthly vegetation indices
- CMR short name `MOD13A3`, version `061`, tile `h19v04`, HDF4, 1 km. One file per month, 60 files, 2021-11 to 2026-10.
- Files named `MOD13A3.A<YYYYDDD>.h19v04.061.<processing timestamp>.hdf`.

### modis_et: MOD16A2GF 8-day evapotranspiration
- CMR short name `MOD16A2GF`, version `061`, tile `h19v04`, HDF4, 500 m. The gap-filled product lags, so the newest granule is 2025-12-27 (A2025361). No gaps inside the range.

### modis_lst: MOD11A2 8-day land surface temperature
- CMR short name `MOD11A2`, version `061`, tile `h19v04`, HDF4, 1 km. 229 files, 2021-11-01 to 2026-10-24.
- One missing 8-day step: **2022-10-16 (A2022289)**. It is not in the folder. It may be absent from the source, so check CMR before treating it as a failed download.

### soilgrids: ISRIC SoilGrids 2.0
- WCS at `https://maps.isric.org/mapserv`, coverage IDs `<property>_<depth>_mean`, GeoTIFF in EPSG:4326, subset to the region.
- Properties: `bdod, cec, cfvo, clay, nitrogen, ocd, phh2o, sand, silt, soc`. Depths: `0-5cm, 5-15cm, 15-30cm, 30-60cm`. That is 10 x 4 = 40 files named `<property>_<depth>_mean.tif`.

### srtm: SRTM GL1 elevation
- CMR short name `SRTMGL1`, version `003`. Six 1° tiles: `N45E022, N45E023, N45E024, N46E022, N46E023, N46E024`, each `<tile>.SRTMGL1.hgt.zip`.

### worldcover: ESA WorldCover 2021 v200
- `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_<tile>_Map.tif`, tiles `N45E021` and `N45E024`.

## Not downloaded
- ECOSTRESS was skipped (sparse, about 13 GB or more for the region). MODIS LST is the stand-in.
- No crop-type map (the US CDL has no Romanian equivalent). WorldCover class 40 is the cropland mask.
