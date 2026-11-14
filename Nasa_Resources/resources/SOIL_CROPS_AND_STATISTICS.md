# Soil, crops, geography and production

| Need | Source | Interpretation |
| --- | --- | --- |
| Soil carbon, pH and texture | [SoilGrids](https://isric.org/explore/soilgrids) · [access documentation](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html) · [raster files](https://files.isric.org/soilgrids/latest/data/) | Modelled baseline; keep soil depth, units and uncertainty |
| Ground soil samples | [LUCAS 2018](https://esdac.jrc.ec.europa.eu/content/lucas-2018-topsoil-data) | Campaign point samples; registration requested |
| Crop-type masks | [JRC EUCROPMAP](https://data.jrc.ec.europa.eu/dataset/15f86c84-eae1-4723-8e00-c1b35c8f56b9) · [2018/2022 catalogue and classes](https://developers.google.com/earth-engine/datasets/catalog/JRC_D5_EUCROPMAP_V1) | Historical snapshots; verify the available classes |
| County/region boundaries | [GISCO NUTS](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics) | Match boundary version and NUTS level |
| Commune/municipality boundaries | [GISCO LAU](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/local-administrative-units) | Local geometry; statistics may remain coarser |
| Romania county crop statistics | [INS TEMPO](http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table) | Search agriculture → area and crop production |
| EU regional comparison | [Eurostat apro_cpshr](https://ec.europa.eu/eurostat/databrowser/view/apro_cpshr/default/table) | NUTS 2; crop/year availability varies |
| National crop statistics | [Eurostat apro_cpsh1](https://ec.europa.eu/eurostat/databrowser/view/apro_cpsh1/default/table) · [metadata](https://ec.europa.eu/eurostat/cache/metadata/en/apro_cp_esms.htm) | Retain moisture basis, unit and flags |
| Production and imports | [FAOSTAT](https://www.fao.org/faostat/en/) | National context; select production or trade domain |
| Crop suitability | [FAO/IIASA GAEZ](https://www.fao.org/gaez/en) | Modelled potential; not measured local yield |
| Crop-water concepts | [FAO crop water needs](https://www.fao.org/4/s2022e/s2022e07.htm) | Calibrate crop-stage assumptions locally |
| Seasonal timing | [JRC ASAP calendars](https://agricultural-production-hotspots.ec.europa.eu/download.php) | Check Romanian crop coverage and local applicability |

## Access findings 

SoilGrids' documentation reports its REST API as paused. Use the documented WCS or WebDAV routes and retain the release information. The file directory was retrieved; complete raster downloads were not tested.

The INS address is corroborated by [Romania's official Eurostat crop metadata](https://ec.europa.eu/eurostat/cache/metadata/en/apro_cp_esqrscn2_ro.htm), but the live TEMPO interface could not be fetched in this review. Use Eurostat as a coarser comparison route if TEMPO is unavailable; do not relabel regional estimates as county observations.

The [LUCAS 2022 landing page](https://esdac.jrc.ec.europa.eu/content/lucas-2022-topsoil-data) describes a prospective public release in early 2027. It is not treated as an available baseline dataset in this pack. Use the accessible campaign and its actual terms.

## Inputs still needed from the team

- Chosen area geometry and administrative identifiers.
- Actual crop histories, planting dates and critical growth-stage windows.
- Confirmation that each target crop is separately represented in the chosen statistics/map; use an explicit broader category if it is not.
- Supplier areas, volumes and actual ingredient specifications, if available.

Do not infer an entire rotation history from a single crop-map year. Aggregated national production is useful context but does not establish a supplier's available volume.
