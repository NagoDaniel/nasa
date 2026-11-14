# Project scope — Path B / SMART FEED

Source: [supplied SPACE2FEED guide](brief/SPACE2FEED_Guide_RO_v1.1.pdf), especially pages 2–6. The local guide is dated 13 November 2026. The [official NASA challenge](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/) remains the authority for NASA submission requirements.

## Product objective

Help farmers compare rotations for soil, water and resilience; then aggregate the results into ingredient sourcing information for the team developing and purchasing pet food.

| Required element in the supplied guide | Resource or evidence |
| --- | --- |
| Romanian analysis area: field or administrative unit | GISCO boundaries or a farmer-provided geometry |
| At least three NASA indicators, shown over at least five years | [NASA catalogue](NASA_DATA.md) |
| Soil organic carbon, texture and pH | SoilGrids; LUCAS for sample context |
| Crop water needs, heat sensitivity and soil effects | Agronomic references plus locally checked crop profiles |
| Farmer priorities: yield, water, soil health and risk | User input, stored with each scenario |
| At least two rotations over 3–4 years | Farmer crop history and explicit candidate scenarios |
| Procurement view | Aggregate by crop/ingredient and sourcing zone |
| Availability, quality and environmental impact | [Indicator definitions](INDICATORS_AND_ASSUMPTIONS.md) |
| Sourcing recommendation and explanations | Scenario assumptions, source IDs and confidence/coverage |
| AI with a defined role | Explain what is modelled, its evaluation and known failure modes |

The guide suggests Alba and neighboring counties; that is a recommendation, not a confirmed team-selected area. Show the farmer workflow first in the pitch. Optional additions include FIRMS, longer-term climate scenarios and a Romanian mobile interface.

## Suggested ingredients in Path B

| English | Romanian in the brief | Keep separate in the data model |
| --- | --- | --- |
| Oats | ovăz | Whole grain, groats and processed product |
| Barley | orz | Crop harvest and delivered ingredient |
| Maize | porumb | Grain, flour, starch and other fractions |
| Peas | mazăre | Whole seed versus protein concentrate |
| Chickpeas | năut | Variety and processing |
| Flax / linseed | in | Seed, meal and oil |
| Sunflower oil | floarea-soarelui (ulei) | Crop output, oil yield and co-products |
| Poultry protein | proteina de pasăre | Feed inputs, poultry production and processing |

## Questions the Path B view should answer

1. Which locally grown plant ingredients could offer more stable supply and a lower estimated environmental impact under stated assumptions?
2. How can the origin and environmental assumptions behind each ingredient be traced back to the field and processing stages?
3. How does sourcing exposure change when an ingredient or source region changes?

Ingredient alternatives must be assessed for their intended pet-food use. A lower sourcing-risk score alone does not establish a nutritionally valid substitution.
