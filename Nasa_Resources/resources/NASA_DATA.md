# NASA data for the six indicator categories

Use these product identifiers in [Earthdata Search](https://search.earthdata.nasa.gov/) or the provider catalogue. Version numbers below describe the reviewed references; retain the version of the files actually used.

| Category | Product and direct documentation | Main scale | Path B use |
| --- | --- | --- | --- |
| Vegetation | [HLS](https://hls.gsfc.nasa.gov/data-products/): HLSL30, HLSS30; HLS-VI for derived indices | 30 m; acquisition-dependent | Spatial crop-vigor patterns |
| Vegetation | [MOD13Q1](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13Q1/), Collection 6.1 | 250 m; 16 days | Consistent historical NDVI/EVI comparison |
| Surface soil moisture | [SPL3SMP v9](https://nsidc.org/data/spl3smp/versions/9), [SPL3SMP_E v6](https://nsidc.org/data/spl3smp_e/versions/6) | 36 km / 9 km grids; daily | Regional moisture context |
| Root-zone soil moisture | [SPL4SMGP v8](https://nsidc.org/data/spl4smgp/versions/8) | 9 km; 3-hourly | Model-assimilated crop-water context |
| Rainfall | [IMERG catalogue](https://gpm.nasa.gov/data/directory): GPM_3IMERGHH / GPM_3IMERGDF, V07 Final | 0.1 degree; half-hourly / daily | Seasonal rainfall and timing |
| Weather | [POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Daily; parameter-dependent grid | Temperature, precipitation, radiation |
| ET / water stress | [ECO_L3T_JET v3](https://data.nasa.gov/dataset/ecostress-tiled-evapotranspiration-pt-jpl-instantaneous-and-daytime-l3-global-70-m-v003), [ECO_L4T_ESI v3](https://data.nasa.gov/dataset/ecostress-tiled-evaporative-stress-index-pt-jpl-instantaneous-l4-global-70-m-v003) | 70 m; irregular acquisitions | Evapotranspiration and evaporative stress |
| Active-fire context | [FIRMS downloads](https://firms.modaps.eosdis.nasa.gov/content/active_fire/), [area API](https://firms.modaps.eosdis.nasa.gov/api/area) | MODIS/VIIRS-dependent | Optional nearby fire signals |

## Choosing and combining products

- Select a common historical window and crop-relevant season. Record valid-observation coverage for every time step.
- HLS/MODIS: mask clouds, shadows and unsuitable quality flags before computing or aggregating indices. Apply documented scaling.
- SMAP: present values at their real support scale; resampling to a field polygon adds no new observations. L4 combines observations with a model.
- IMERG: do not mix Early/Late/Final runs silently. For half-hourly rates in mm/hour, multiply by 0.5 hours before summing; an already accumulated daily product must not be integrated a second time.
- POWER: preserve units, missing-value definitions and UTC/local-solar-time choice. Meteorological and radiation histories need not have the same start date.
- ECOSTRESS: distinguish instantaneous and daily estimates, retain model names and uncertainty, and disclose gaps. ET alone does not separate irrigation water from rain-derived water.
- FIRMS: describe detections as hotspots unless independent evidence establishes agricultural burning.

The [SMAP L4 page](https://nsidc.org/data/spl4smgp/versions/8) reports reprocessing for 14 May–28 July 2026. If those dates are present in team files, check their generation date and replacement status.

## Optional climate scenarios

[NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/) provides daily downscaled scenarios at 0.25 degree. Keep the model, scenario, realization and baseline together. Use it for longer-term adaptation scenarios, rather than treating it as an operational seasonal forecast.

## Public access routes

[AppEEARS documentation](https://appeears.earthdatacloud.nasa.gov/api/) explains point/area tasks and product discovery. [CMR](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) supports collection/granule discovery. Product support, authorization and downloadable coverage must be checked for the selected collection.
