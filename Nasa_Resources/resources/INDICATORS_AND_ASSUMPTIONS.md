# Indicators and assumptions

The following are proposed analytical definitions for the project, not validated forecasts or fixed agronomic thresholds. The source links support the inputs; the team must justify and evaluate its scoring method.

| Dimension | Candidate measure | Inputs | What it can support |
| --- | --- | --- | --- |
| Availability | Seasonal NDVI/EVI anomaly against the same seasonal window | HLS/MOD13Q1 and crop mask | Evidence of atypical vegetation condition |
| Availability | Soil-moisture percentile/anomaly | SMAP and a consistent baseline | Regional moisture pressure |
| Availability | Seasonal rainfall total and timing | IMERG or POWER | Water-input variability |
| Availability | Historical area, yield and production variability | INS/Eurostat/FAOSTAT | Production baseline at the published geography |
| Quality | Heat/humidity/rain exposure in a documented critical crop stage | POWER/IMERG and crop calendar | Weather-related quality risk screening |
| Environment: water | ET and evaporative-stress context | ECOSTRESS plus rainfall/moisture | Water-use/stress patterns; not an irrigation meter |
| Environment: soil | Baseline organic carbon, pH and texture; rotation attributes | SoilGrids/LUCAS and crop profiles | Soil suitability and scenario explanation |
| Environment: climate | Ingredient mass × compatible LCA factor | ECO-ALIM/GLEAM and processing assumptions | A boundary-specific impact estimate |
| Optional disturbance | Nearby active-fire detections | FIRMS with crop masks and independent context | Hotspot exposure, not proof of residue burning |

Input details and citations: [NASA_DATA.md](NASA_DATA.md), [SOIL_CROPS_AND_STATISTICS.md](SOIL_CROPS_AND_STATISTICS.md), [PATH_B_INGREDIENTS.md](PATH_B_INGREDIENTS.md).

## Interpretation rules

- An NDVI anomaly is not a yield estimate unless its relationship to yield has been fitted and evaluated for the relevant crop/area.
- A five-year baseline can support a demonstration but does not justify strong claims about rare-event probabilities.
- Do not report a measured annual carbon gain from a static soil layer or from merely adding a legume to a scenario.
- Crop water use, irrigation withdrawal and water scarcity are different quantities.
- Weather-based quality risk needs local stage definitions and calibration. It does not replace ingredient testing.
- Coarse products can be aggregated with a field view, but their real resolution must remain visible.
- Keep independent observations, modelled quantities, statistical proxies and scenario assumptions separately labelled.

## Rotation and sourcing comparisons

Compare at least two plausible 3–4-year rotations. Use user-selected priorities and document the score direction, normalization, weights and missing-data behavior. Preserve seasonal crop differences instead of averaging unrelated crop stages together.

For ingredient sourcing, aggregate only using known crop areas or explicit sourcing weights. Unknown supplier volumes should remain unknown. If risk scores are combined by ingredient mass share, describe the result as an exposure index unless the method has been calibrated as a probability.

Each result should retain source IDs, coverage period, spatial support, valid-data share, method version, assumptions and the scope of its confidence statement. Evaluate any predictive model with geographically or temporally separated validation appropriate to its intended use.

## Project information not supplied by these public sources

Real supplier contracts, current farm crop histories, laboratory results, ingredient processing yields, commercial recipe constraints and verified site-specific emission factors may require team or partner input. Public references provide context; they should not be presented as those missing records.
