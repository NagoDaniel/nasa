# Access and team workflow

## Accounts and routes

| Route | What a teammate needs |
| --- | --- |
| Earthdata Search and many NASA files | Their authorized Earthdata sign-in and any collection-specific authorization |
| AppEEARS | Earthdata authentication for user tasks; select a currently supported product/version |
| POWER | Public API requests; no Earthdata login |
| FIRMS area API | A free MAP_KEY; direct recent-file routes are separate |
| Copernicus / Earth Engine | Their own account/project setup where required |
| SoilGrids | Public files/WCS; REST API reported paused |
| LUCAS 2018 | Provider registration/request and use conditions |
| ECO-ALIM full database | Provider download form and CAPTCHA |
| Eurostat / FAOSTAT | Public data interfaces; JavaScript may be required |

An existing browser session is not part of this repository and does not grant teammates access. Use stable provider URLs instead of expiring signed download URLs. Never put credentials, cookies or tokens into the catalogue or Git history.

## Work with the data already downloaded

1. Register each actual file or collection subset in [data/download-manifest.json](data/download-manifest.json).
2. Record its source ID, exact product/version, dates, bounding area, variables, units, coordinate system, processing timestamp and checksum.
3. Verify the common five-year coverage, then choose the analysis window and aggregation area.
4. Apply scale factors, missing-value handling and QA masks before aggregation.
5. Store derived indicators with their source record IDs and valid-data coverage.
6. Link every displayed score to its underlying evidence and assumptions.

## Discovering or replacing missing inputs

- In [Earthdata Search](https://search.earthdata.nasa.gov/), search the exact short name from [NASA_DATA.md](NASA_DATA.md), choose the product version, then set area and dates.
- In [AppEEARS](https://appeears.earthdatacloud.nasa.gov/api/), inspect the current product catalogue before creating a point/area task.
- Use the [CMR API documentation](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) for programmatic discovery; metadata access and data-file authorization are distinct.
- Use provider DOI/citation metadata to pin the collection. Do not infer a version from a display name alone.

## Verification vocabulary in sources.json

| Status | Meaning |
| --- | --- |
| provider_documentation_reviewed | Provider/distributor text or catalogue content was retrieved |
| web_app_entry_confirmed | Entry URL was retrieved; interactive query/export was not exercised |
| web_app_entry_and_provider_metadata_reviewed | App entry and its provider metadata were reviewed |
| indexed_official_description_only | Official search-index description found; full page fetch unsuccessful |
| official_reference_only | URL supported by official metadata; live interface not verified |
| provider_index_link_only_fetch_timeout | Provider index lists the link; detail page retrieval timed out |

`dataset_download_tested: false` means no end-to-end download test was performed while preparing this catalogue. It does not mean the dataset is unavailable.

## Data in GitHub

Keep documentation, schemas, small permitted derived examples and the manifest in Git. `data/raw/` and `data/processed/` are ignored by default so that adding a local dataset does not accidentally stage large files. Use a suitable shared data location when needed and record a stable access route plus checksum. The `.gitignore` here protects only this resource directory; retain appropriate rules in the repository root as well.
