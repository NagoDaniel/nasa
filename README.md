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

## AI assistant

A chat button on the map opens the dashboard assistant. **Its role:** find areas, open
sections, colour the map, and explain the numbers that are already in this dashboard.

- **Deterministic first.** Place names ("zoom to Aiud", "Ineu" → pick one of two), section
  commands ("open soil") and greetings are handled by plain code, no AI involved.
- **Google Gemini** (`gemini-2.5-flash` by default) handles other questions. It can only
  call fixed, read-only tools that run the dashboard's own code over this project's data
  (indicators, season hazards, soil, INS statistics, rotation scores, procurement scores)
  and propose UI actions (select area, open section, colour map). It cannot write, browse
  or fetch anything else.
- **Where it fails:** it can misread a question, pick the wrong commune when names repeat,
  or word a number loosely. Numbers in a reply that do not appear in the tool data are
  flagged with ⚠. Coarse grids (POWER ~50 km, GLDAS ~25 km) describe the region, not a field.
- **Safety:** 500-character messages, per-IP rate limits (6/min, 60/day) and a global daily
  AI budget, prompt-injection screening before the model, signed history (clients cannot
  forge earlier assistant turns), output cleaning (no links/HTML) and a leak canary. The
  API key stays on the server. Messages are not stored.

Enable it by putting the key in `backend/.env` (see `backend/.env.example`):

```bash
S2F_GEMINI_API_KEY=your-key
```

Without a key the assistant still navigates (place names, sections). Run the backend with a
single worker: rate limits are kept in memory.

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
- AI: Google Gemini API (assistant only; answers are generated from the data above)
- Crop traits: FAO (Brouwer & Heibloem 1986; FAO-56), FAO Ecocrop, IPCC 2019 / AR6, Peoples et al. 2009, Preissel et al. 2015, Seifert et al. 2017

Rebuild the processed data from the raw downloads in `backend/.cache/raw/` (see `dataset.md`):

```bash
cd backend && uv run --group process python scripts/process/build_all.py
```
