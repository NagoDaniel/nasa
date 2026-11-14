# SMART FEED — Path B resource hub

SPACE2FEED / Transavia · NASA Field Shift · Resources reviewed 14 November 2026

**Purpose:** one GitHub-ready home for the data sources and references behind a farmer rotation tool and a pet-food ingredient sourcing view.

Path B covers **oats, barley, maize, peas, chickpeas, flax/linseed, sunflower oil and poultry protein**. The farmer-facing NASA component remains central. The supplied brief asks for at least three NASA indicators over a minimum of five years and comparison of at least two rotations over 3–4 years.

## Start here

| File | What it provides |
| --- | --- |
| [PROJECT_BRIEF.md](PROJECT_BRIEF.md) | Path B scope, requirements and ingredient mapping |
| [NASA_DATA.md](NASA_DATA.md) | The six requested indicator categories, exact product names and limitations |
| [SOIL_CROPS_AND_STATISTICS.md](SOIL_CROPS_AND_STATISTICS.md) | Soil, crop maps, geography, production and agronomy |
| [PATH_B_INGREDIENTS.md](PATH_B_INGREDIENTS.md) | Ingredient composition, pet-food nutrition, quality and environmental impact |
| [ACCESS_AND_WORKFLOW.md](ACCESS_AND_WORKFLOW.md) | Accounts, download routes, access issues and processing workflow |
| [INDICATORS_AND_ASSUMPTIONS.md](INDICATORS_AND_ASSUMPTIONS.md) | How sources support availability, quality and environmental indicators |
| [SOURCES.md](SOURCES.md) | Complete clickable catalogue, grouped by topic |
| [sources.json](sources.json) | The same catalogue in machine-readable form |
| [CITATIONS.md](CITATIONS.md) | Attribution and reproducibility instructions |
| [data/README.md](data/README.md) | How to register the datasets already downloaded by the team |
| [data/download-manifest.json](data/download-manifest.json) | Empty inventory for real downloaded files |
| [brief/SPACE2FEED_Guide_RO_v1.1.pdf](brief/SPACE2FEED_Guide_RO_v1.1.pdf) | Supplied Romanian participant guide, unchanged |

## Practical starting set

Use the team's downloaded coverage first. A compact implementation can combine MOD13Q1 vegetation, SMAP moisture and POWER weather, plus soil properties, a crop-area mask, regional production statistics and an ingredient reference table. HLS and ECOSTRESS add spatial detail when coverage and time allow. IMERG provides an alternative rainfall record. FIRMS and long-term climate projections are optional in the supplied brief.

A five-year overlap such as **2021–2025** is a starting suggestion, not a confirmed dataset range or a decision about the project geography. Check the actual files before selecting the baseline. Five years satisfies the brief's minimum but is a short climatological reference.

## What is verified

This is a **curated source and documentation pack**, not a copy of every dataset. Provider descriptions and access requirements were reviewed; full downloads were not tested in this task. The team's previously downloaded files have not been supplied for inspection, so the download inventory is intentionally empty.

Source records distinguish reviewed documentation, JavaScript entry pages and references whose live interface could not be fetched. Authentication still applies when a teammate opens a data service.

Notable access/coverage notes:

- SoilGrids reports its REST API as paused; its documentation lists WCS and WebDAV alternatives.
- INS TEMPO's address is supported by official metadata, but its live interface could not be verified here.
- SMAP L4 has a provider reprocessing notice for 14 May–28 July 2026.
- The linked pet-food PEFCR page gives an end-of-2025 validity date; current validity was not established.
- The official challenge Resources tab could not be fetched; the event mirror is a secondary navigation reference.

See the linked source records in [SOURCES.md](SOURCES.md) for details and evidence.

## Mirror into GitHub

Copy this entire `resources/` directory into your repository. The Markdown uses relative file links, so the same layout works in GitHub. Preserve the `.gitignore` inside this directory. Record real data files in the manifest; keep large rasters in `data/raw/` locally or in suitable shared data storage with stable, authorized links.

This pack includes no account credentials, API keys or browser-session data. The provided guide retains its original ownership, and linked materials retain their providers' terms.
