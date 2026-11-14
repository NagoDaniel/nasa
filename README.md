# SPACE2FEED — Field Shift (NASA Space Apps 2026, Alba Iulia)

Decision-support tool for farmers (crop rotations, soil and water) with a procurement
lens for the Transavia **SMART FEED** (pet food) direction: oats, barley, maize, pea,
chickpea, flax, sunflower.

*Built at the NASA Space Apps Challenge. Not endorsed by NASA.*

## Stack

| Part | Tech |
|---|---|
| Frontend | React + TypeScript (Vite), MapLibre GL |
| Backend | Python 3.12, FastAPI (uv) |
| App data | SQLite (`backend/app.db`, via SQLModel): farms, fields, priorities |
| NASA + geo data | **plain JSON files** in `backend/data/`, loaded once into memory |

## Run

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend on port 8000. API docs: http://localhost:8000/docs

## Data layout

```
backend/data/
  geo/      counties, regions, communes, outline, mask, labels (*.geojson.json)
  nasa/     one JSON per dataset; schema in data/nasa/README.md
  crops/    smart_feed.json
```

Rebuild the boundary layers (downloads sources into `backend/.cache/`):

```bash
cd backend && uv run --group scripts python scripts/build_boundaries.py
```

## Map

- All 41 counties + București (dissolved from cadastre UATs, so every border level lines up exactly)
- 8 development regions (NUTS-2), coloured with a distinct shade per county
- Commune / town (UAT) borders and labels for Alba + neighbours (Arad, Bihor, Cluj, Hunedoara, Mureș, Sibiu, Vâlcea) from zoom 8
- Everything outside Romania is masked; hillshaded relief

## Data sources & attribution

- Boundaries: [geoBoundaries](https://www.geoboundaries.org) ROU ADM1 (World Bank) / ADM2 (ANCPI), CC BY 4.0
- Commune names (diacritics): © OpenStreetMap contributors, ODbL
- Basemap: [OpenFreeMap](https://openfreemap.org), © OpenMapTiles, © OpenStreetMap contributors
- Terrain: Mapzen / AWS Terrain Tiles
- NASA: POWER daily (MERRA-2 / CERES), GPM IMERG Final V07B, GLDAS Noah 2.1, FIRMS VIIRS S-NPP, MODIS MOD13Q1 (via AppEEARS; sample so far)
- ISRIC SoilGrids 2.0 (CC BY 4.0); JRC EUCROPMAP 2018/2022 (CC BY 4.0, © European Union); INS TEMPO Online (AGR108A/109A/110A)
- Crop traits: FAO (Brouwer & Heibloem 1986; FAO-56), FAO Ecocrop, IPCC 2019 / AR6, Peoples et al. 2009, Preissel et al. 2015, Seifert et al. 2017

Rebuild the processed data from the raw downloads in `backend/.cache/raw/` (see `dataset.md`):

```bash
cd backend && uv run --group process python scripts/process/build_all.py
```
