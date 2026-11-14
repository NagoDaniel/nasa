# Complete source catalogue

54 curated source entries. Documentation reviewed 2026-11-14.

Access requirements and limitations are part of each entry. A working documentation link does not establish that every data download has been tested.

The unchanged participant guide is included at [brief/SPACE2FEED_Guide_RO_v1.1.pdf](brief/SPACE2FEED_Guide_RO_v1.1.pdf).

## Challenge

### challenge-official

**[Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)** · NASA Space Apps

Official challenge and final authority for the NASA submission.

- Access: Public documentation.
- Note: Indexed official description found; the full page and Resources tab could not be fetched during this review.
- Review status: `indexed_official_description_only`; dataset download not tested.

### challenge-mirror

**[Field Shift challenge and resource-list mirror](https://hackathlone.com/challenges/adapting-farms-with-nasa-data)** · HackAthlone

Readable event-host copy for navigation when the official page is unavailable.

- Access: Public documentation.
- Note: Secondary source, used only to cross-reference the challenge list. NASA remains authoritative. HLS and FIRMS are not separately named in this copy.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### transavia-reports

**[Transavia sustainability reports](https://www.transavia.ro/en/sustainability-reports/)** · Transavia

Company context, supply-chain boundaries and published sustainability reporting.

- Access: Public documentation.
- Note: Company-level figures are not ingredient-specific emission factors or supplier commitments.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

## NASA indicators

### hls

**[Harmonized Landsat Sentinel-2 data products](https://hls.gsfc.nasa.gov/data-products/)** · NASA GSFC / LP DAAC

Field-scale vegetation monitoring; surface reflectance and HLS-VI indices.

- Access: Public documentation; Earthdata authentication for the standard download workflow.
- Product/search terms: `HLSL30`; `HLSS30`; `HLS-VI`.
- Scale/time: 30 m; acquisition-dependent.
- Note: Use a consistent collection and cloud/quality masks. Frequent overpasses do not guarantee cloud-free observations.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### mod13q1

**[MODIS Terra vegetation indices](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD13Q1/)** · NASA LAADS DAAC / LP DAAC

NDVI/EVI time series for historical vegetation comparisons.

- Access: Public catalogue; Earthdata authentication for data downloads.
- Product/search terms: `MOD13Q1`; `Collection 6.1 / 061`.
- Scale/time: 250 m; 16-day composites.
- Note: Apply quality flags, fill-value handling and the documented scale factor. Pixels can mix multiple fields/crops.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### smap-l3

**[SMAP L3 radiometer soil moisture, Version 9](https://nsidc.org/data/spl3smp/versions/9)** · NASA NSIDC DAAC

Daily surface-soil moisture context.

- Access: Public documentation; Earthdata authentication for standard downloads.
- Product/search terms: `SPL3SMP`; `009`.
- Scale/time: 36 km grid; daily.
- Note: Regional context; a grid value is not a measurement of an individual small farm.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### smap-l3-enhanced

**[SMAP Enhanced L3 soil moisture, Version 6](https://nsidc.org/data/spl3smp_e/versions/6)** · NASA NSIDC DAAC

Enhanced surface-soil moisture product.

- Access: Public documentation; Earthdata authentication for standard downloads.
- Product/search terms: `SPL3SMP_E`; `006`.
- Scale/time: 9 km grid; daily.
- Note: Enhanced grid spacing is not equivalent to independent field-scale detail.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### smap-l4

**[SMAP L4 surface and root-zone soil moisture, Version 8](https://nsidc.org/data/spl4smgp/versions/8)** · NASA NSIDC DAAC

Model-assimilated surface and root-zone moisture for regional water-stress assessment.

- Access: Public documentation; Earthdata authentication for standard downloads.
- Product/search terms: `SPL4SMGP`; `008`.
- Scale/time: 9 km grid; 3-hourly.
- Note: Provider notice: L4 data for 14 May–28 July 2026 are being reprocessed after a geolocation issue. Check processing status if those dates are used; record version and retrieval date.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### imerg

**[GPM precipitation data directory](https://gpm.nasa.gov/data/directory)** · NASA GPM / GES DISC / PPS

Rainfall totals, timing and anomalies; links to half-hourly and daily IMERG products.

- Access: Public directory; Earthdata for GES DISC, separate registration for PPS routes.
- Product/search terms: `GPM_3IMERGHH (Final half-hourly)`; `GPM_3IMERGDF (Final daily)`; `V07`.
- Scale/time: 0.1 degree grid; half-hourly/daily.
- Note: Record Early/Late/Final run. Final is delayed. Distinguish precipitation rate from accumulated depth.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### power

**[NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)** · NASA LaRC POWER

Temperature, precipitation and solar-radiation time series for the selected location.

- Access: Public API; no Earthdata login required.
- Product/search terms: `T2M`; `T2M_MAX`; `T2M_MIN`; `PRECTOTCORR`; `ALLSKY_SFC_SW_DWN`.
- Scale/time: Daily; spatial resolution depends on source parameter.
- Note: Choose the agroclimatology community and record units/time standard. These are gridded data, not a field weather station; start dates differ by parameter.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ecostress-et

**[ECOSTRESS tiled evapotranspiration, Version 3](https://data.nasa.gov/dataset/ecostress-tiled-evapotranspiration-pt-jpl-instantaneous-and-daytime-l3-global-70-m-v003)** · NASA LP DAAC

Evapotranspiration estimates for spatial water-use comparisons.

- Access: Public documentation; Earthdata authentication for standard downloads.
- Product/search terms: `ECO_L3T_JET`; `003`.
- Scale/time: 70 m; irregular observation times.
- Note: Keep model/layer, time basis, uncertainty and cloud flags. Do not treat irregular scenes as an uninterrupted daily record.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ecostress-esi

**[ECOSTRESS tiled evaporative stress index, Version 3](https://data.nasa.gov/dataset/ecostress-tiled-evaporative-stress-index-pt-jpl-instantaneous-l4-global-70-m-v003)** · NASA LP DAAC

Water-stress context from actual-to-potential evapotranspiration.

- Access: Public documentation; Earthdata authentication for standard downloads.
- Product/search terms: `ECO_L4T_ESI`; `003`.
- Scale/time: 70 m; irregular observation times.
- Note: Interpret the product-specific ESI definition and flags; verify historical coverage before promising five years of valid observations.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### firms-download

**[FIRMS active-fire downloads](https://firms.modaps.eosdis.nasa.gov/content/active_fire/)** · NASA LANCE FIRMS

Optional active-fire/hotspot evidence near crop-sourcing areas.

- Access: Public recent-data downloads; archive access follows provider workflow.
- Product/search terms: `MODIS`; `VIIRS`.
- Scale/time: Sensor-dependent; near-real-time products.
- Note: A thermal detection alone does not establish agricultural burning or burned area.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### nex-cmip6

**[NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/)** · NASA NCCS

Optional long-term climate scenarios for rotation resilience.

- Access: Public documentation and documented THREDDS/AWS routes.
- Product/search terms: `NEX-GDDP-CMIP6`.
- Scale/time: 0.25 degree; daily scenarios.
- Note: Climate projections are not next-season weather forecasts; retain model, experiment, realization and version.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

## Access tools

### ecostress-access

**[ECOSTRESS data access](https://ecostress.jpl.nasa.gov/data)** · NASA JPL

Entry points to Earthdata, AppEEARS and ECOSTRESS documentation.

- Access: Public documentation.
- Note: Mission pages and catalogue pages can update at different times; pin the exact downloaded product version.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### firms-api

**[FIRMS area API](https://firms.modaps.eosdis.nasa.gov/api/area)** · NASA LANCE FIRMS

Programmatic fire detections for a bounding box and time window.

- Access: Free FIRMS MAP_KEY required.
- Note: Keep the key outside Git. API limits and archive availability depend on the selected source.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### earthdata-search

**[Earthdata Search](https://search.earthdata.nasa.gov/)** · NASA Earthdata

Locate collections and files by product, area and date.

- Access: JavaScript app; Earthdata login for many downloads.
- Review status: `web_app_entry_confirmed`; dataset download not tested.

### appeears

**[AppEEARS API documentation](https://appeears.earthdatacloud.nasa.gov/api/)** · NASA LP DAAC

Point/area extraction workflows and current supported-product catalogue.

- Access: Public documentation; account authentication for user tasks.
- Note: Confirm product/version support in the catalogue; do not assume all products in this folder are supported.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### cmr

**[Common Metadata Repository Search API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)** · NASA Earthdata

Discover exact collection identifiers, granules, metadata and data links.

- Access: Public metadata API; file download authorization is separate.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### worldview

**[NASA Worldview](https://worldview.earthdata.nasa.gov/)** · NASA Earthdata

Visual checks and map illustrations.

- Access: Public JavaScript app.
- Note: A rendered map image is not a substitute for numeric analysis data.
- Review status: `web_app_entry_confirmed`; dataset download not tested.

### copernicus

**[Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/)** · European Union / ESA

Supplementary Sentinel imagery and data-access documentation.

- Access: Public documentation; separate Copernicus account for relevant services.
- Note: Earthdata credentials do not automatically grant access to Copernicus services.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### soilgrids-access

**[SoilGrids access documentation](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html)** · ISRIC

WCS/WebDAV alternatives and access limitations.

- Access: Public documentation.
- Note: REST API is reported paused as of this review. Use documented alternative routes; their full download workflows were not tested.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ecoalim-download

**[ECO-ALIM download form](https://eng-ecoalim.hub.inrae.fr/database-eco-alim/downloading-of-the-database)** · INRAE / ECO-ALIM

Obtain the provider database through its official form.

- Access: Name/email/organization form and CAPTCHA; no form submitted during this review.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

## Soil, crops and geography

### soilgrids

**[SoilGrids](https://isric.org/explore/soilgrids)** · ISRIC

Baseline soil organic carbon, pH and texture with prediction uncertainty.

- Access: Public maps; CC BY 4.0.
- Scale/time: 250 m; standard soil-depth intervals.
- Note: Static modelled soil properties do not measure the annual effect of a proposed rotation.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### soilgrids-files

**[SoilGrids raster directory](https://files.isric.org/soilgrids/latest/data/)** · ISRIC

VRT mosaics and GeoTIFF tiles for local processing.

- Access: Public directory.
- Note: Record the actual release behind latest and subset the area; whole-world layers are large.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### lucas-2018

**[LUCAS 2018 topsoil data](https://esdac.jrc.ec.europa.eu/content/lucas-2018-topsoil-data)** · European Commission JRC / ESDAC

Ground-sample soil context and independent comparison with modelled soils.

- Access: Registration/request required.
- Scale/time: Point samples; survey campaign.
- Note: Sparse points are not parcel-wide measurements. Use the provider conditions for reuse and redistribution.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### eucropmap-jrc

**[EUCROPMAP 2018 dataset record](https://data.jrc.ec.europa.eu/dataset/15f86c84-eae1-4723-8e00-c1b35c8f56b9)** · European Commission JRC

Crop-type mapping and crop-area masks.

- Access: Public catalogue with download/service routes.
- Product/search terms: `EUCROPMAP 2018`.
- Scale/time: 10 m; 2018 snapshot.
- Note: A historical map cannot establish a field crop or rotation in 2026.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### eucropmap-ee

**[EUCROPMAP 2018 and 2022 catalogue](https://developers.google.com/earth-engine/datasets/catalog/JRC_D5_EUCROPMAP_V1)** · Google Earth Engine / JRC data

Distributor documentation and class legend for the 2018/2022 maps.

- Access: Public documentation; Earth Engine use requires its own setup.
- Product/search terms: `JRC/D5/EUCROPMAP/V1`.
- Scale/time: 10 m; selected reference years.
- Note: Confirm crop classes before use: not every Path B crop is separately identifiable. These are not complete annual crop histories.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### gisco-nuts

**[GISCO NUTS statistical boundaries](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics)** · Eurostat / European Commission

Regional/county geometry for aggregation and joins to official statistics.

- Access: Public downloads subject to provider use conditions.
- Note: Match boundary year, NUTS level, coordinate system and statistics geography.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### gisco-lau

**[GISCO local administrative units](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/local-administrative-units)** · Eurostat / European Commission

Municipality/commune geography where local aggregation is appropriate.

- Access: Public downloads subject to provider use conditions.
- Note: Local boundaries do not imply local crop statistics are available.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### gaez

**[Global Agro-Ecological Zoning](https://www.fao.org/gaez/en)** · FAO / IIASA

Crop suitability and production-potential context; links to GAEZ v5.

- Access: Public documentation and geospatial platform.
- Product/search terms: `GAEZ v5`.
- Note: Suitability and potential yield are model outputs, not observed production. Keep scenario/input-level assumptions.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### fao-water

**[Crop water needs](https://www.fao.org/4/s2022e/s2022e07.htm)** · FAO

Reference concepts for crop stage, crop coefficient and evapotranspiration.

- Access: Public documentation.
- Note: Indicative requirements need local climate, variety, calendar and management calibration.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### asap-calendars

**[ASAP downloads and crop calendars](https://agricultural-production-hotspots.ec.europa.eu/download.php)** · European Commission JRC

Crop-calendar reference and seasonal indicator context.

- Access: Public documentation.
- Note: Check country/crop coverage; confirm local flowering and harvest dates with agronomic knowledge.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

## Production and trade

### ins-tempo

**[INS TEMPO agriculture and crop-production tables](http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table)** · Romanian National Institute of Statistics

Romanian county cultivated area, harvested production and yield.

- Access: Public portal; live interface not verified.
- Note: Portal reference is confirmed by Romania’s official Eurostat metadata. Direct retrieval failed here; verify table titles, units, crops and year coverage in TEMPO.
- Review status: `official_reference_only`; dataset download not tested.
- Official corroboration: [provider metadata](https://ec.europa.eu/eurostat/cache/metadata/en/apro_cp_esqrscn2_ro.htm).

### eurostat-regional

**[Crop production in EU standard humidity by NUTS 2](https://ec.europa.eu/eurostat/databrowser/view/apro_cpshr/default/table)** · Eurostat

Regional comparison of crop area and production.

- Access: Public data browser/downloads.
- Product/search terms: `apro_cpshr`.
- Scale/time: Annual; NUTS 2.
- Note: Not county/parcel data. Check crop and year coverage, statistical flags and units.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### eurostat-national

**[Crop production in EU standard humidity](https://ec.europa.eu/eurostat/databrowser/view/apro_cpsh1/default/table)** · Eurostat

Romanian and EU national crop statistics.

- Access: Public JavaScript data browser/downloads.
- Product/search terms: `apro_cpsh1`.
- Scale/time: Annual; national.
- Review status: `web_app_entry_and_provider_metadata_reviewed`; dataset download not tested.

### eurostat-methods

**[Crop-production metadata](https://ec.europa.eu/eurostat/cache/metadata/en/apro_cp_esms.htm)** · Eurostat

Units, moisture conventions and statistical comparability.

- Access: Public documentation.
- Note: Some methods and categories change from the 2025 reference year. Keep original metadata and flags.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### faostat

**[FAOSTAT data portal](https://www.fao.org/faostat/en/)** · FAO

National production and trade context for local-versus-imported ingredient sourcing.

- Access: Public JavaScript portal.
- Product/search terms: `Crops and livestock products`; `Trade: crops and livestock products`.
- Scale/time: Annual; country-level.
- Note: Navigate to the required domain; values are not individual suppliers, contracts or current quotations.
- Review status: `web_app_entry_confirmed`; dataset download not tested.

## Path B ingredients

### feedtables

**[INRAE-CIRAD-AFZ feed-material tables](https://www.feedtables.com/)** · INRAE / CIRAD / AFZ

Ingredient identity, composition and feed-material context.

- Access: Public documentation.
- Note: Farm-animal feed values do not establish dog/cat digestibility or suitability. Supplier specifications and species-specific assessment remain separate.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-oats

**[Oats](https://www.feedtables.com/content/oats)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Distinguish whole grain, groats and processed forms.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-barley

**[Barley](https://www.feedtables.com/content/barley)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Match processing and moisture basis.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-maize

**[Maize](https://www.feedtables.com/content/maize)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Match grain versus flour, starch or by-products.
- Review status: `provider_index_link_only_fetch_timeout`; dataset download not tested.

### ingredient-peas

**[Pea](https://www.feedtables.com/content/pea)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Whole peas and protein concentrates are different ingredients.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-chickpea

**[Chickpea, kabuli type](https://www.feedtables.com/content/chickpea-kabuli-type)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Variety and processing affect composition.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-flax

**[Linseed, whole](https://www.feedtables.com/content/linseed-whole)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Whole seed, oil and meal need separate specifications.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-sunflower-oil

**[Sunflower oil](https://www.feedtables.com/content/sunflower-oil)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Use oil-specific processing yield and impact allocation.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ingredient-poultry

**[Processed poultry proteins, protein 60–70%](https://www.feedtables.com/content/processed-animal-proteins-poultry-protein-60-70)** · INRAE / CIRAD / AFZ

Composition reference for the Path B ingredient catalogue.

- Access: Public documentation.
- Note: Reference ingredient only; actual poultry material and processing must be specified.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

## Pet food and impacts

### fediaf-nutrition

**[Nutritional guidelines for cats and dogs](https://europeanpetfood.org/self-regulation/nutritional-guidelines/)** · FEDIAF

Species/life-stage constraints when considering ingredient substitutions.

- Access: Public reading/download; copyrighted publication.
- Product/search terms: `2025 edition linked by provider`.
- Note: Link to the publication rather than redistributing it. This folder provides no validated complete pet-food formulation.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### fediaf-safety

**[Guide to good practice for safe pet food](https://europeanpetfood.org/self-regulation/safety/)** · FEDIAF

Manufacturing, handling and storage context for ingredient-quality risks.

- Access: Public reading/download; copyrighted publication.
- Note: A remote-sensing risk signal is not a product safety certificate.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ecoalim

**[ECO-ALIM feed ingredient environmental database](https://eng-ecoalim.hub.inrae.fr/database-eco-alim)** · INRAE / IFIP and project partners

Ingredient-level life-cycle assessment references.

- Access: Public description; database download form.
- Note: Check geography, system boundary, production practice, year and allocation before comparing factors.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### ecoalim-methods

**[Environmental data methodology](https://www.feedtables.com/content/environmental-data)** · INRAE-CIRAD-AFZ / ECO-ALIM

Interpret feed LCA values and differences between field, storage and factory boundaries.

- Access: Public documentation.
- Note: French-context and historical factors are proxies when applied to Romania; identify the proxy and its limitations.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### gleam

**[GLEAM tools and data](https://www.fao.org/gleam/tools-and-data/en)** · FAO

Poultry supply-chain emissions and water-use methodology.

- Access: Public documentation, data tools and model resources.
- Note: Livestock-system results are not automatically factors for rendered poultry protein. Specify co-product allocation and processing.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### fediaf-pef

**[Pet-food Product Environmental Footprint Category Rules](https://europeanpetfood.org/sustainability/product-environmental-footprint-category-rules-pefcr-for-pet-food/)** · FEDIAF

Methodological reference for pet-food life-cycle boundaries and comparable product categories.

- Access: Public reference; current validity must be checked.
- Note: The page states validity through 31 December 2025 for its February 2025 update. No later extension was verified; do not claim current PEF conformity.
- Review status: `provider_documentation_reviewed`; dataset download not tested.

### efsa-mycotoxins

**[Mycotoxins](https://www.efsa.europa.eu/en/topics/topic/mycotoxins)** · EFSA

Scientific context for weather-related quality risk in food/feed ingredients.

- Access: Public documentation.
- Note: Weather can support risk screening; contamination and concentration require direct evidence such as laboratory testing.
- Review status: `provider_documentation_reviewed`; dataset download not tested.
