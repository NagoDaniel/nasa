"""Language of API texts: English by default, Romanian with ?lang=ro on any request.

- `lang()` is the language of the current request (set by a middleware in main.py).
- `t(key, **kw)` formats a sentence template (TEMPLATES) for texts built from numbers.
- `L(s)` / `localize(obj)` translate fixed strings (data-file labels and notes, method
  notes) by exact match (STATIC). Identifier-like strings (`maize`, `partly_cloudy`,
  `heat35_jul_aug`) are never touched, so the frontend's keys stay intact.
- `crop(c)`, `texture(s)`, `months(s)` translate names that are also used as ids.
English output is unchanged when no language is given.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any

_LANG: ContextVar[str] = ContextVar("s2f_lang", default="en")
LANGS = ("en", "ro")


def set_lang(value: str | None):
    return _LANG.set(value if value in LANGS else "en")


def reset_lang(token) -> None:
    _LANG.reset(token)


def lang() -> str:
    return _LANG.get()


def ro() -> bool:
    return _LANG.get() == "ro"


# ----------------------------------------------------------------------------- names used as ids too
CROPS_RO = {
    "maize": "porumb", "wheat": "grâu", "barley": "orz", "oats": "ovăz", "pea": "mazăre", "chickpea": "năut",
    "soy": "soia", "sunflower": "floarea-soarelui", "flax": "in", "rapeseed": "rapiță", "grain_legumes": "leguminoase boabe",
}
FAMILIES_RO = {"cereal": "cereale", "legume": "leguminoase", "oilseed (Asteraceae)": "oleaginoase (Asteraceae)",
               "oilseed (Linaceae)": "oleaginoase (Linaceae)", "oilseed": "oleaginoase"}
TEXTURES_RO = {
    "clay": "argilos", "clay loam": "lutos-argilos", "loam": "lutos", "sandy clay loam": "luto-argilos nisipos",
    "sandy loam": "luto-nisipos", "silty clay": "argilos prăfos", "silty clay loam": "luto-argilos prăfos",
    "sandy clay": "argilo-nisipos", "silt loam": "luto-prăfos", "silt": "prăfos", "loamy sand": "nisipo-lutos", "sand": "nisipos",
}
CROPMAP_RO = {
    "artificial": "zone construite", "common wheat": "grâu comun", "durum wheat": "grâu dur", "barley": "orz", "rye": "secară",
    "oats": "ovăz", "maize": "porumb", "rice": "orez", "triticale": "triticale", "other cereals": "alte cereale",
    "potatoes": "cartofi", "sugar beet": "sfeclă de zahăr", "other root crops": "alte rădăcinoase",
    "other industrial crops": "alte plante tehnice", "sunflower": "floarea-soarelui", "rapeseed": "rapiță", "soya": "soia",
    "dry pulses": "leguminoase boabe", "fodder crops": "plante furajere", "bare arable land": "teren arabil necultivat",
    "woodland / shrubland": "pădure / tufărișuri", "grassland": "pajiști", "bare land": "teren fără vegetație",
    "water": "apă", "wetlands": "zone umede",
}
LANDCOVER_RO = {
    "tree cover": "pădure", "shrubland": "tufărișuri", "grassland": "pajiști", "cropland": "teren arabil",
    "built-up": "zone construite", "bare / sparse vegetation": "teren gol / vegetație rară", "snow and ice": "zăpadă și gheață",
    "permanent water": "ape permanente", "herbaceous wetland": "zone umede ierboase", "mangroves": "mangrove",
    "moss and lichen": "mușchi și licheni",
}


def crop(c: str) -> str:
    return CROPS_RO.get(c, c) if ro() else c


def crops(cs) -> str:
    return ", ".join(crop(c) for c in cs)


def family(f: str) -> str:
    return FAMILIES_RO.get(f, f) if ro() else f


def texture(s: str | None) -> str | None:
    return TEXTURES_RO.get(s, s) if (ro() and s) else s


def cropclass(s: str) -> str:
    return CROPMAP_RO.get(s, s) if ro() else s


def landcover(s: str) -> str:
    return LANDCOVER_RO.get(s, s) if ro() else s


_MONTHS = {"Jan": "ian", "Feb": "feb", "Mar": "mar", "Apr": "apr", "May": "mai", "Jun": "iun", "Jul": "iul",
           "Aug": "aug", "Sep": "sep", "Oct": "oct", "Nov": "nov", "Dec": "dec"}
_MONTH_RE = re.compile(r"\b(" + "|".join(_MONTHS) + r")\b")
_WINDOW_RE = re.compile(r"^(?:(?:late|early|mid|\d{1,2})\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b[\s\w–\-/()]*$")


def months(s: str) -> str:
    """'late May–Jun' -> 'sfârșit mai–iun'; '1–20 Oct' -> '1–20 oct' (Romanian only)."""
    if not ro() or not s:
        return s
    out = _MONTH_RE.sub(lambda m: _MONTHS[m.group(1)], s)
    for a, b in (("late ", "sfârșit "), ("early ", "început "), ("mid ", "mijloc "), ("mid-", "mijloc "),
                 ("(winter)", "(de toamnă)"), ("(spring)", "(de primăvară)")):
        out = out.replace(a, b)
    return out


def pct(x: float, nd: int = 0) -> str:
    """'10%' / '10 %' style kept as in English; decimal comma in Romanian."""
    s = f"{x:.{nd}%}"
    return s.replace(".", ",") if ro() else s


def num(x: float, nd: int = 0) -> str:
    """Number with thousands separators: 1,234.5 (EN) / 1.234,5 (RO)."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",").replace(" ", ".") if ro() else s


# ----------------------------------------------------------------------------- sentence templates
TEMPLATES: dict[str, tuple[str, str]] = {
    # hazards (scoring/hazards.py)
    "hz_heat35_jul_aug": ("≥ 3 days at Tmax ≥ 35 °C in Jul–Aug", "≥ 3 zile cu Tmax ≥ 35 °C în iul–aug"),
    "hz_heat32_jul_aug": ("≥ 20 days at Tmax ≥ 32 °C in Jul–Aug", "≥ 20 de zile cu Tmax ≥ 32 °C în iul–aug"),
    "hz_rootmoist_jja_z": ("summer root-zone soil moisture ≥ 1 std below the 2015–2025 mean",
                           "umiditatea solului în zona rădăcinilor vara cu ≥ 1 abatere standard sub media 2015–2025"),
    "hz_dry_spell_apr_sep": ("a dry spell of ≥ 15 days in Apr–Sep", "o perioadă secetoasă de ≥ 15 zile în apr–sep"),
    "hz_rain_flowering_small_grain": ("≥ 200 mm rain in 15 May–30 Jun", "≥ 200 mm ploaie în 15 mai–30 iun"),
    "hz_wet_days_flowering_small_grain": ("≥ 32 wet days (≥ 1 mm) in 15 May–30 Jun", "≥ 32 de zile ploioase (≥ 1 mm) în 15 mai–30 iun"),
    "hz_late_frost": ("≥ 4 frost days in 15 Apr–31 May", "≥ 4 zile cu îngheț în 15 apr–31 mai"),
    "hz_heat30_jun": ("≥ 5 days at Tmax ≥ 30 °C in June", "≥ 5 zile cu Tmax ≥ 30 °C în iunie"),
    "hz_rain_harvest_small_grain": ("≥ 100 mm rain in July", "≥ 100 mm ploaie în iulie"),
    "hz_rain_harvest_summer_crops": ("≥ 150 mm rain in Sep–Oct", "≥ 150 mm ploaie în sep–oct"),

    # rotation scoring (scoring/rotation.py)
    "rot_wrap_repeat": (" (rotation repeats)", " (rotația se repetă)"),
    "rot_wrap_last": (" (last year's crop)", " (cultura de anul trecut)"),
    "rot_after_legume": ("+{p} after {prev}{wrap}", "+{p} după {prev}{wrap}"),
    "rot_repeat": ("−{p} same crop as the year before{wrap}", "−{p} aceeași cultură ca în anul precedent{wrap}"),
    "rot_ph": ("−5% soil pH outside optimum", "−5% pH-ul solului în afara optimului"),
    "f_yield_label": ("{crop}: local yield vs Romania (median 2015–2025)", "{crop}: randament local față de România (mediana 2015–2025)"),
    "f_yield_value": ("{c} vs {r} kg/ha ({x}×)", "{c} față de {r} kg/ha ({x}×)"),
    "f_no_stats": ("no statistics", "fără statistici"),
    "f_yield_assume": ("Score 60 = Romanian average; scales with the ratio.", "Scorul 60 = media României; crește proporțional cu raportul."),
    "f_ph_label": ("{crop}: soil pH fit", "{crop}: potrivirea pH-ului solului"),
    "f_ph_value": ("pH {ph} vs optimum {lo}–{hi}", "pH {ph} față de optimul {lo}–{hi}"),
    "f_ph_source": ("SoilGrids 2.0 (median 0–30 cm); optimum {ref}", "SoilGrids 2.0 (mediana 0–30 cm); optim {ref}"),
    "f_ph_assume": ("−5% yield assumed without liming.", "Se presupune −5% randament fără amendare cu var."),
    "f_water_label": ("{crop}: water need vs dry-year rain (Apr–Sep)", "{crop}: necesarul de apă față de ploaia unui an secetos (apr–sep)"),
    "f_water_value": ("needs {lo}–{hi} mm; dry-year rain {dry} mm (average {avg} mm)",
                      "necesar {lo}–{hi} mm; ploaie în an secetos {dry} mm (media {avg} mm)"),
    "f_water_source": ("Need: {ref}. Rain: NASA POWER, driest 20% of 2015–2025.",
                       "Necesar: {ref}. Ploaie: NASA POWER, cei mai secetoși 20% din anii 2015–2025."),
    "f_water_assume": ("Rain-fed; winter crops also use soil water stored over winter, so their water score is conservative.",
                       "Neirigat; culturile de toamnă folosesc și apa înmagazinată în sol peste iarnă, deci scorul lor de apă e prudent."),
    "f_risk_label": ("{crop}: sensitive period ({stage}, {window}) hit by hazards",
                     "{crop}: perioada sensibilă ({stage}, {window}) afectată de riscuri"),
    "f_risk_value": ("{n} of {m} years — {list}", "{n} din {m} ani — {list}"),
    "f_none": ("none", "niciunul"),
    "f_risk_source": ("NASA POWER + GLDAS yearly indicators", "Indicatori anuali NASA POWER + GLDAS"),
    "f_thresholds": ("Hazard thresholds: {list}.", "Praguri de risc: {list}."),
    "f_cv_label": ("{crop}: year-to-year yield swing in the county", "{crop}: variația randamentului de la an la an în județ"),
    "f_cv_value": ("coefficient of variation {cv}", "coeficient de variație {cv}"),
    "f_cv_assume": ("Risk score = 100 × (1 − (0.6 × hazard-year share + 0.4 × min(1, CV / 40%))).",
                    "Scorul de risc = 100 × (1 − (0,6 × ponderea anilor cu riscuri + 0,4 × min(1, CV / 40%)))."),
    "f_legume_label": ("Grain legume years", "Ani cu leguminoase boabe"),
    "f_of": ("{a} of {b}", "{a} din {b}"),
    "f_legume_source": ("Crop traits (PEOPLES09)", "Caracteristicile culturilor (PEOPLES09)"),
    "f_legume_assume": ("0 legumes = 0, 1 = 20, ≥ 2 = 30 points. Legumes fix nitrogen and break cereal disease cycles.",
                        "0 leguminoase = 0, 1 = 20, ≥ 2 = 30 de puncte. Leguminoasele fixează azotul și întrerup ciclul bolilor cerealelor."),
    "f_families_label": ("Crop families", "Familii de culturi"),
    "f_traits": ("Crop traits", "Caracteristicile culturilor"),
    "f_families_assume": ("1 family = 0, 2 = 15, 3 = 25, ≥ 4 = 30 points.", "1 familie = 0, 2 = 15, 3 = 25, ≥ 4 = 30 de puncte."),
    "f_winter_label": ("Winter soil cover", "Sol acoperit iarna"),
    "f_winter_value": ("{a} of {b} years with a winter crop", "{a} din {b} ani cu o cultură de toamnă"),
    "f_winter_assume": ("Up to 20 points; covered soil over winter limits erosion and nitrate leaching.",
                        "Până la 20 de puncte; solul acoperit iarna limitează eroziunea și pierderea nitraților."),
    "f_interval_label": ("Rotation intervals", "Intervale de rotație"),
    "f_interval_bad": ("{crop} returns after {n} year(s) (needs ≥ {gap})", "{crop} revine după {n} an(i) (necesită ≥ {gap})"),
    "f_interval_ok": ("all crops respect their return interval", "toate culturile respectă intervalul de revenire"),
    "f_interval_source": ("Crop traits (AGRO)", "Caracteristicile culturilor (AGRO)"),
    "f_interval_assume": ("20 points, −10 per violation (disease build-up).", "20 de puncte, −10 pentru fiecare abatere (acumulare de boli)."),
    "f_soc_label": ("Soil organic carbon here (context)", "Carbon organic în sol aici (context)"),
    "f_soc_value": ("{v} g/kg (0–30 cm, {tex})", "{v} g/kg (0–30 cm, {tex})"),
    "f_context_only": ("Shown for context; not part of the score.", "Arătat pentru context; nu intră în scor."),
    "f_slope_label": ("Cropland slope here (context)", "Panta terenului arabil aici (context)"),
    "f_slope_value": ("mean {m} %; {s} % of cropland ≥ 10 % slope", "medie {m} %; {s} % din terenul arabil are pantă ≥ 10 %"),
    "f_slope_source": ("NASA SRTM GL1 (30 m) + ESA WorldCover 2021 cropland", "NASA SRTM GL1 (30 m) + teren arabil ESA WorldCover 2021"),
    "f_slope_assume": ("Shown for context; not part of the score. On slopes ≥ ~10 % bare soil erodes quickly, so the years without "
                       "winter cover ({bare}) matter most there.",
                       "Arătat pentru context; nu intră în scor. Pe pante ≥ ~10 % solul descoperit se erodează repede, deci anii fără "
                       "cultură de toamnă ({bare}) contează cel mai mult acolo."),
    "rot_conf_base": ("Crop yields are county statistics (INS); climate comes from ~25–50 km grids.",
                      "Randamentele sunt statistici pe județ (INS); clima provine din grile de ~25–50 km."),
    "rot_conf_commune": ("For a commune, these are the county's yields and the surrounding region's climate.",
                         "Pentru o comună, acestea sunt randamentele județului și clima regiunii din jur."),
    "rot_conf_sparse": ("Chickpea / flax have sparse or proxy statistics.", "Năutul / inul au statistici rare sau aproximate."),
    "ins_note": ("INS TEMPO AGR110A", "INS TEMPO AGR110A"),
    "ins_proxy_note": ("INS TEMPO — 'grain legumes' (yield = production ÷ area) used as proxy; no chickpea statistics",
                       "INS TEMPO — „leguminoase boabe” (randament = producție ÷ suprafață) folosite ca aproximare; nu există statistici pentru năut"),

    # procurement (scoring/procurement.py)
    "pr_nodata_title": ("Not enough production data", "Date de producție insuficiente"),
    "pr_nodata_text": ("INS reports too little {crop} production in these counties to rank sourcing areas.",
                       "INS raportează prea puțină producție de {crop} în aceste județe pentru a ordona zonele de aprovizionare."),
    "pr_spread_title": ("Split purchases between two reliable counties", "Împărțiți achizițiile între două județe sigure"),
    "pr_spread_text": ("Source {crop} from {a} and {b}: both score well on availability and quality, and their yields moved together only "
                       "weakly (r = {r}, 2015–2025), so a bad year in one is less likely to hit the other.",
                       "Cumpărați {crop} din {a} și {b}: ambele au scoruri bune la disponibilitate și calitate, iar randamentele lor s-au mișcat "
                       "împreună doar slab (r = {r}, 2015–2025), deci un an prost într-unul e mai puțin probabil să-l lovească și pe celălalt."),
    "pr_q_all": ("all counties with {y} data", "toate județele cu date pentru {y}"),
    "pr_q_seg": ("In {y} the {crop} sensitive period was hit — {parts}.", "În {y}, perioada sensibilă a culturii de {crop} a fost afectată — {parts}."),
    "pr_q_note": (" {y} weather data exist only for {have}; the other counties show their latest season ({old}).",
                  " Date meteo pentru {y} există doar pentru {have}; celelalte județe arată ultimul lor sezon ({old})."),
    "pr_q_title": ("Check {years} lots for weather-related quality problems", "Verificați loturile din {years} pentru probleme de calitate cauzate de vreme"),
    "pr_q_test": (" Test incoming lots (e.g. mycotoxins) before blending.", " Testați loturile primite (de ex. micotoxine) înainte de amestecare."),
    "pr_alt_title": ("Consider {alt} as a partial substitute", "Luați în calcul {alt} ca înlocuitor parțial"),
    "pr_alt_text": ("In this region {alt} scores {s} on availability + quality versus {m} for {crop} ({group} ingredient group). "
                    "Test it in recipes as a partial replacement to spread weather risk.",
                    "În această regiune, {alt} are scorul {s} la disponibilitate + calitate față de {m} pentru {crop} (grupa de ingrediente {group}). "
                    "Testați-l în rețete ca înlocuitor parțial, pentru a împărți riscul meteo."),
    "pr_group_protein": ("protein", "proteice"), "pr_group_energy": ("energy", "energetice"), "pr_group_oil": ("oil", "oleaginoase"),
    "pr_contract_title": ("Contract farmers who add pea to their rotation", "Contractați fermieri care introduc mazărea în rotație"),
    "pr_contract_text": ("If a quarter of the {crop} area in these counties ({area} ha in the latest year) grew pea one year in four, "
                         "about {ha} ha/yr would be pea: ≈ {pea_t} t pea (≈ {p_lo}–{p_hi} t protein), ≈ {n_t} t less fertiliser N and "
                         "≈ {co2} t CO2e less field N2O per year, plus a yield bonus for the following cereal. Offer contracts or premiums to these farmers.",
                         "Dacă un sfert din suprafața de {crop} din aceste județe ({area} ha în ultimul an) ar avea mazăre un an din patru, "
                         "ar fi circa {ha} ha/an de mazăre: ≈ {pea_t} t mazăre (≈ {p_lo}–{p_hi} t proteină), ≈ {n_t} t mai puțin azot din îngrășăminte și "
                         "≈ {co2} t CO2e mai puțin N2O din câmp pe an, plus un spor de randament pentru cereala următoare. Oferiți acestor fermieri contracte sau prime."),
    "pr_contract_a1": ("25% of the crop's area, pea once in a 4-year rotation (replaces this crop that year).",
                       "25% din suprafața culturii, mazăre o dată într-o rotație de 4 ani (înlocuiește cultura în acel an)."),
    "pr_contract_a2": ("Pea yield = median county pea yield 2015–2025 (INS); protein 21–25% of dry seed.",
                       "Randamentul mazării = mediana pe județ 2015–2025 (INS); proteină 21–25% din bobul uscat."),
    "pr_contract_a3": ("Fertiliser N: mid-range of crop traits; N2O via IPCC EF1 1%, GWP100 273. Estimate only.",
                       "Azot din îngrășăminte: mijlocul intervalului din caracteristicile culturii; N2O după IPCC EF1 1%, GWP100 273. Doar o estimare."),
    "pr_a_avail": ("Availability = 100 × (1 − 0.5 × min(1, yield CV / 40%) − 0.5 × share of hazard years); production volume is shown alongside.",
                   "Disponibilitate = 100 × (1 − 0,5 × min(1, CV randament / 40%) − 0,5 × ponderea anilor cu riscuri); volumul producției e arătat alături."),
    "pr_a_quality": ("Quality = 100 × (1 − share of years in which the crop's sensitive window was hit; 2015–2025, plus 2026 where NASA POWER has 2026 data).",
                     "Calitate = 100 × (1 − ponderea anilor în care perioada sensibilă a culturii a fost afectată; 2015–2025, plus 2026 unde NASA POWER are date pentru 2026)."),
    "pr_a_ndvi": ("Cropland greenness = Apr–Aug mean MODIS NDVI over cropland pixels, latest season vs the mean of the earlier seasons (2022 onward). "
                  "All crops together; shown as context, not part of the scores.",
                  "Verdeața terenului arabil = NDVI MODIS mediu apr–aug pe pixelii de teren arabil, ultimul sezon față de media sezoanelor anterioare (din 2022). "
                  "Toate culturile împreună; arătat pentru context, nu intră în scoruri."),
    "pr_a_impact": ("Impact = mean of water score (dry-year Apr–Sep rain ÷ crop water need) and emissions score (100 at 0, 0 at ≥ 400 kg CO2e/t).",
                    "Impact = media scorului de apă (ploaia apr–sep a unui an secetos ÷ necesarul culturii) și a scorului de emisii (100 la 0, 0 la ≥ 400 kg CO2e/t)."),
    "pr_a_emis": ("Emissions are field N2O only: mid-range N fertiliser ({lo}–{hi} kg N/ha) × IPCC EF1 1% × 44/28 × GWP100 273 ÷ 5-year median yield. "
                  "Fertiliser manufacture, fuel and transport are not included.",
                  "Emisiile sunt doar N2O din câmp: azot la mijlocul intervalului ({lo}–{hi} kg N/ha) × IPCC EF1 1% × 44/28 × GWP100 273 ÷ randamentul median pe 5 ani. "
                  "Producția îngrășămintelor, combustibilul și transportul nu sunt incluse."),
    "pr_s_ins": ("INS TEMPO AGR108A/109A/110A (area, production, yield), county level", "INS TEMPO AGR108A/109A/110A (suprafață, producție, randament), la nivel de județ"),
    "pr_s_weather": ("NASA POWER daily and NASA GLDAS Noah monthly (hazard years, rain)", "NASA POWER zilnic și NASA GLDAS Noah lunar (ani cu riscuri, ploaie)"),
    "pr_s_fires": ("NASA FIRMS VIIRS (vegetation fires)", "NASA FIRMS VIIRS (incendii de vegetație)"),
    "pr_s_ndvi": ("NASA MODIS MOD13A3 NDVI on ESA WorldCover 2021 cropland (season greenness)",
                  "NASA MODIS MOD13A3 NDVI pe terenul arabil ESA WorldCover 2021 (verdeața sezonului)"),
    "pr_s_traits": ("Crop traits: FAO (Brouwer & Heibloem 1986; FAO-56), IPCC 2019, AR6", "Caracteristicile culturilor: FAO (Brouwer & Heibloem 1986; FAO-56), IPCC 2019, AR6"),
    "pr_o_names_all": ("the 8 study counties", "cele 8 județe studiate"),
    "pr_o_low_title": ("Expect less {crop} from {names} in {y}", "Așteptați mai puțin {crop} din {names} în {y}"),
    "pr_o_low_action": ("Secure volume early or shift part of the purchase to other counties / an alternative ingredient.",
                        "Asigurați volumul din timp sau mutați o parte din achiziție în alte județe / spre un ingredient alternativ."),
    "pr_o_good_title": ("Good {y} {crop} outlook in {names}", "Perspectivă bună pentru {crop} în {y} în {names}"),
    "pr_o_good_action": ("A good moment to contract volume from these counties.", "Un moment bun pentru a contracta volume din aceste județe."),
    "pr_o_norm_title": ("Normal {y} {crop} outlook in {names}", "Perspectivă normală pentru {crop} în {y} în {names}"),
    "pr_o_norm_action": ("No change to the buying plan needed from the weather signal.", "Semnalul meteo nu cere schimbarea planului de achiziții."),
    "pr_o_weak": (" The weather signal is weak (the model beats a trend-only guess by only 5–10 %), so treat this as a hint.",
                  " Semnalul meteo e slab (modelul bate o estimare doar pe tendință cu numai 5–10 %), deci tratați-l ca pe un indiciu."),
    "pr_o_text": ("Weather-based forecast for {names}: about {p} t (likely {lo}–{hi} t) vs {n} t in a normal year ({pct} %).",
                  "Prognoză pe baza vremii pentru {names}: circa {p} t (probabil {lo}–{hi} t) față de {n} t într-un an normal ({pct} %)."),
    "pr_o_drag": (" Main drag: {label} ({e} %).", " Principala frână: {label} ({e} %)."),
    "pr_o_weakest": (" Weakest: {list}.", " Cele mai slabe: {list}."),

    # season forecast (scoring/forecast.py)
    "fc_trend": ("Long-term trend", "Tendința pe termen lung"),
    "fc_year": ("year", "an"),
    "fc_m1": ("Yield anomaly (yield ÷ county median − 1) = ridge regression on the crop's sensitive-window weather indicators plus a year trend, "
              "pooled over the 8 counties, 2000–2025 (penalty λ = {lam} on standardised predictors).",
              "Abaterea randamentului (randament ÷ mediana județului − 1) = regresie ridge pe indicatorii meteo din perioada sensibilă a culturii plus "
              "o tendință anuală, pe toate cele 8 județe, 2000–2025 (penalizare λ = {lam} pe predictori standardizați)."),
    "fc_m2": ("Tested leave-one-year-out: each year is predicted by a model that never saw it. Errors and intervals come from these tests.",
              "Testat lăsând câte un an deoparte: fiecare an e prognozat de un model care nu l-a văzut. Erorile și intervalele vin din aceste teste."),
    "fc_m3": ("Benchmark: a normal year = the long-term trend alone. Weather signal: strong if adding the weather cuts the benchmark error by ≥ {strong}, "
              "weak at {weak}–{strong}, none below (then the range is just the usual swing around the trend).",
              "Reper: un an normal = doar tendința pe termen lung. Semnal meteo: puternic dacă vremea reduce eroarea reperului cu ≥ {strong}, "
              "slab la {weak}–{strong}, absent sub acest prag (atunci intervalul e doar variația obișnuită în jurul tendinței)."),
    "fc_m4": ("More indicators were tested (summer Tmax, Apr–Sep rain, GDD, early soil wetness): they made held-out errors worse, so each crop keeps "
              "only its own sensitive-window indicators.",
              "Au fost testați mai mulți indicatori (Tmax de vară, ploaia apr–sep, GDD, umiditatea timpurie a solului): au mărit erorile la anii testați, "
              "deci fiecare cultură păstrează doar indicatorii perioadei ei sensibile."),
    "fc_m5": ("Normal for the forecast season = the trend level with average weather; the verdict and drivers show the weather effect only.",
              "Normalul pentru sezonul prognozat = nivelul tendinței cu vreme medie; verdictul și factorii arată doar efectul vremii."),
    "fc_m6": ("Intervals = percentiles of the held-out errors: the 80 % interval held 8 in 10 past years, the 50 % interval 1 in 2.",
              "Intervalele = percentile ale erorilor la anii testați: intervalul de 80 % a fost corect în 8 din 10 ani trecuți, cel de 50 % în 1 din 2."),
    "fc_m7": ("Supply = latest INS area × yield; assumes the area planted does not change. Normal = same area × normal (trend) yield.",
              "Oferta = ultima suprafață INS × randament; presupune că suprafața cultivată nu se schimbă. Normal = aceeași suprafață × randament normal (tendință)."),
    "fc_l1": ("County level: INS publishes yields per county only; a field can differ a lot.",
              "Nivel de județ: INS publică randamente doar pe județ; o parcelă poate diferi mult."),
    "fc_l2": ("26 seasons: extremes worse than anything since 2000 are not learned; intervals assume the future errs like the past.",
              "26 de sezoane: extremele mai grave decât orice din 2000 încoace nu sunt învățate; intervalele presupun că viitorul greșește ca trecutul."),
    "fc_l3": ("Weather and a straight-line trend only: prices, fertiliser, pests and area changes are not in the model; a county whose yields stopped "
              "rising (e.g. Alba maize since 2018) may get a normal that is too high.",
              "Doar vremea și o tendință liniară: prețurile, îngrășămintele, dăunătorii și schimbările de suprafață nu sunt în model; un județ ale cărui "
              "randamente au încetat să crească (de ex. porumbul din Alba din 2018) poate primi un normal prea mare."),
    "fc_l4": ("Weather is NASA POWER at ~50 km; associations, not proof of cause.", "Vremea vine din NASA POWER la ~50 km; asocieri, nu dovezi de cauzalitate."),
    "fc_l5": ("The latest season can still change: POWER's last weeks are provisional and late crops may not be harvested yet.",
              "Ultimul sezon se mai poate schimba: ultimele săptămâni din POWER sunt provizorii, iar culturile târzii poate nu sunt încă recoltate."),
    "fc_s1": ("INS TEMPO AGR110A (county yield 2000–2025), AGR108A / AGR109A (area, production)",
              "INS TEMPO AGR110A (randament pe județ 2000–2025), AGR108A / AGR109A (suprafață, producție)"),
    "fc_s2": ("NASA POWER daily, 2000–2026 (derived/forecast_inputs.json)", "NASA POWER zilnic, 2000–2026 (derived/forecast_inputs.json)"),
    "fc_s3": ("Crop sensitive windows: crop_traits.json", "Perioadele sensibile ale culturilor: crop_traits.json"),

    # map layers (maplayers.py)
    "ml_soil": ("{label} (0–30 cm)", "{label} (0–30 cm)"),
    "ml_cropshare": ("{cls}: share of arable land", "{cls}: pondere din terenul arabil"),

    # planner (planner/*.py, routers/planner.py)
    "pl_sow_winter": ("Sow in autumn, {w} (the year before harvest).", "Semănat toamna, {w} (în anul dinaintea recoltei)."),
    "pl_sow_spring": ("Soil warm enough (7-day mean ≥ {th} °C){frost} by {start} in a typical year; by {safe} in 8 of 10 years.",
                      "Sol destul de cald (media pe 7 zile ≥ {th} °C){frost} până la {start} într-un an obișnuit; până la {safe} în 8 din 10 ani."),
    "pl_sow_frost": (" and past the last frost", " și după ultimul îngheț"),
    "pl_no_planter": ("No row-crop planter: {list} left out.", "Fără semănătoare de precizie: {list} excluse."),
    "pl_n_limit": ("Nitrogen limit {lim} kg/ha: {list} need more and were left out.", "Limită de azot {lim} kg/ha: {list} au nevoie de mai mult și au fost excluse."),
    "pl_must": ("{crop} kept because you must grow it.", "{crop} păstrat pentru că trebuie să-l cultivați."),
    "pl_price_own": ("your price", "prețul dvs."),
    "pl_price_ins": ("INS farm-gate price, {reg}, median {a}–{b}", "Preț INS la poarta fermei, {reg}, mediana {a}–{b}"),
    "pl_romania": ("Romania", "România"),
    "pl_level": ("your field {p} % vs county ({n} {seasons})", "parcela dvs. {p} % față de județ ({n} {seasons})"),
    "pl_season": ("season", "sezon"), "pl_seasons": ("seasons", "sezoane"),
    "pl_after": ("+{p} after {prev}", "+{p} după {prev}"),
    "pl_repeat": ("−{p} same crop as the year before", "−{p} aceeași cultură ca în anul precedent"),
    "pl_ph": ("−5 % soil pH {ph} outside {lo}–{hi}", "−5 % pH-ul solului {ph} în afara intervalului {lo}–{hi}"),
    "pl_err_no_crop": ("No crop is left after your answers (considered / refused / machinery / nitrogen). Allow more crops.",
                       "Nu a rămas nicio cultură după răspunsurile dvs. (luate în calcul / refuzate / utilaje / azot). Permiteți mai multe culturi."),
    "pl_autumn_passed": ("The autumn sowing window for the {y} harvest has passed, so year 1 is a spring crop.",
                         "Perioada de semănat de toamnă pentru recolta din {y} a trecut, deci anul 1 e o cultură de primăvară."),
    "pl_err_no_rot": ("No rotation fits: the return gaps after what grew here and your 'must grow' crop rule out every sequence. "
                      "Allow more crops or fewer years of the must-grow crop.",
                      "Nicio rotație nu se potrivește: intervalele de revenire după ce s-a cultivat aici și cultura „obligatorie” exclud orice succesiune. "
                      "Permiteți mai multe culturi sau mai puțini ani cu cultura obligatorie."),
    "pl_basis_trend": ("county trend {a}–{b}, ranges from held-out years", "tendința județului {a}–{b}, intervale din anii testați"),
    "pl_basis_ins": ("INS county yields 2015–2025 ({why})", "randamente INS pe județ 2015–2025 ({why})"),
    "pl_proxy": ("grain legumes as proxy", "leguminoase boabe ca aproximare"),
    "pl_no_series": ("no long series", "fără serie lungă"),

    # drawn fields (field/*.py, routers/fields.py)
    "fd_not_polygon": ("Field must be a GeoJSON Polygon", "Parcela trebuie să fie un poligon GeoJSON"),
    "fd_one_ring": ("Field must have exactly one outer ring and no holes", "Parcela trebuie să aibă un singur contur, fără goluri"),
    "fd_corners": ("Field needs 3–{n} corners", "Parcela are nevoie de 3–{n} colțuri"),
    "fd_bad_coord": ("Invalid coordinate", "Coordonată invalidă"),
    "fd_romania": ("Field must be in Romania", "Parcela trebuie să fie în România"),
    "fd_crosses": ("Field outline crosses itself; move the corners so the edges do not cross",
                   "Conturul parcelei se intersectează; mutați colțurile ca laturile să nu se încrucișeze"),
    "fd_min": ("Field is {ha} ha; the minimum is {min} ha", "Parcela are {ha} ha; minimul este {min} ha"),
    "fd_max": ("Selection is {ha} ha; the maximum is {max} ha", "Selecția are {ha} ha; maximul este {max} ha"),
    "fd_under1": ("Under 1 ha: only a handful of 30 m HLS pixels fall inside; treat field values as rough.",
                  "Sub 1 ha: în interior intră doar câțiva pixeli HLS de 30 m; tratați valorile ca aproximative."),
    "fd_outside": ("Outside the study area (Alba and neighbours): only imagery is available here.",
                   "În afara zonei de studiu (Alba și vecinii): aici sunt disponibile doar imaginile din satelit."),
    "fd_default_name": ("Field {ha} ha", "Parcelă {ha} ha"),
    "fd_cell_note": ("One value for each {res} cell. Your field covers only a tiny part of it, and the value is the same everywhere inside the cell; "
                     "it does not show differences within a town or between fields.",
                     "O singură valoare pentru fiecare celulă {res}. Parcela dvs. acoperă doar o mică parte din ea, iar valoarea e aceeași peste tot în celulă; "
                     "nu arată diferențe în interiorul unei localități sau între parcele."),
    "fd_scene_skip": ("Scene ≥ {p}% cloud: pixels not read", "Scenă cu ≥ {p}% nori: pixelii nu au fost citiți"),
    "fd_read_error": ("Could not read this image", "Imaginea nu a putut fi citită"),
    "fd_read_error_hls": ("Could not read this image (Earthdata login?)", "Imaginea nu a putut fi citită (autentificare Earthdata?)"),
    "fd_spike": ("NDVI {v} differs by more than {d} from the clear images on {d1} ({v1}) and {d2} ({v2}): possible undetected cloud or haze",
                 "NDVI {v} diferă cu mai mult de {d} față de imaginile fără nori din {d1} ({v1}) și {d2} ({v2}): posibil nor sau ceață nedetectată"),
    "fd_rule_clear": ("≥ {p}% of field pixels clear", "≥ {p}% din pixelii parcelei fără nori"),
    "fd_rule_partly": ("{a}–{b}% clear: value shown, flagged", "{a}–{b}% fără nori: valoare arătată, marcată"),
    "fd_rule_cloudy": ("< {a}% clear, or whole scene ≥ {s}% cloud (pixels not read): no value",
                       "< {a}% fără nori sau scena întreagă ≥ {s}% nori (pixeli necitiți): fără valoare"),
    "fd_rule_nodata": ("field outside the image swath / no pixels", "parcela în afara imaginii / fără pixeli"),
    "fd_rule_error": ("image could not be read", "imaginea nu a putut fi citită"),
    "fd_rule_suspect": ("value jumps > {d} away from clear images on both sides (≤ {days} days): possible undetected cloud, flagged and not used",
                        "valoarea sare cu > {d} față de imaginile fără nori de pe ambele părți (≤ {days} zile): posibil nor nedetectat, marcată și nefolosită"),
    "fd_index": ("NDVI = (NIR − Red) / (NIR + Red), surface reflectance; median of the clear field pixels",
                 "NDVI = (NIR − Roșu) / (NIR + Roșu), reflectanță la suprafață; mediana pixelilor fără nori ai parcelei"),
}


def t(key: str, **kw: Any) -> str:
    en, r = TEMPLATES[key]
    return (r if ro() else en).format(**kw)


# ----------------------------------------------------------------------------- fixed strings (exact match)
STATIC: dict[str, str] = {
    # data/nasa + data/cells labels
    "Vegetation fire detections": "Incendii de vegetație detectate",
    "Evapotranspiration": "Evapotranspirație",
    "Potential evaporation": "Evaporare potențială",
    "Rainfall (model forcing)": "Ploaie (date de intrare ale modelului)",
    "Root-zone soil moisture (0–100 cm)": "Umiditatea solului în zona rădăcinilor (0–100 cm)",
    "Topsoil moisture (0–10 cm)": "Umiditatea stratului superior (0–10 cm)",
    "Total water storage anomaly (groundwater + soil + surface)": "Abaterea rezervei totale de apă (subterană + sol + suprafață)",
    "Precipitation (satellite)": "Precipitații (satelit)",
    "Evapotranspiration on cropland (satellite)": "Evapotranspirație pe terenul arabil (satelit)",
    "Daytime land surface temperature on cropland": "Temperatura suprafeței ziua, pe terenul arabil",
    "Night-time land surface temperature on cropland": "Temperatura suprafeței noaptea, pe terenul arabil",
    "Vegetation index on cropland (NDVI)": "Indicele de vegetație pe terenul arabil (NDVI)",
    "Vegetation index, all land (NDVI)": "Indicele de vegetație, tot terenul (NDVI)",
    "Potential evapotranspiration on cropland (satellite)": "Evapotranspirație potențială pe terenul arabil (satelit)",
    "Frost days (Tmin < 0 °C)": "Zile cu îngheț (Tmin < 0 °C)",
    "Growing degree days (base 10 °C)": "Grade-zile de creștere (bază 10 °C)",
    "Hot days (Tmax ≥ 32 °C)": "Zile caniculare (Tmax ≥ 32 °C)",
    "Precipitation (POWER, bias-corrected)": "Precipitații (POWER, corectate)",
    "Relative humidity": "Umiditate relativă",
    "Root-zone soil wetness": "Umezeala solului în zona rădăcinilor",
    "Mean daily maximum temperature": "Temperatura maximă zilnică medie",
    "Mean air temperature": "Temperatura medie a aerului",
    "Surface soil moisture (satellite, 0–5 cm)": "Umiditatea solului la suprafață (satelit, 0–5 cm)",
    # units
    "days": "zile", "days/yr": "zile/an", "mm/yr": "mm/an", "°C·day": "°C·zi", "°C·day/yr": "°C·zi/an", "fires/yr": "incendii/an",
    "fires": "incendii", "z-score": "scor z", "cm": "cm",
    # resolutions
    "375 m points": "puncte de 375 m",
    "0.25° grid (~25 km)": "grilă de 0,25° (~25 km)",
    "~300 km (3° mascons on a 0.5° grid)": "~300 km (mascon-uri de 3° pe o grilă de 0,5°)",
    "0.1° grid (~11 km)": "grilă de 0,1° (~11 km)",
    "0.5° × 0.625° grid (~50 km)": "grilă de 0,5° × 0,625° (~50 km)",
    "9 km EASE-Grid 2.0": "grilă EASE 2.0 de 9 km",
    "10 m map, counted at 100 m (1 pixel = 1 ha)": "hartă de 10 m, numărată la 100 m (1 pixel = 1 ha)",
    "10 m map, counted at ~90 m": "hartă de 10 m, numărată la ~90 m",
    "250 m (resampled to ~0.0023° in this project)": "250 m (reeșantionat la ~0,0023° în acest proiect)",
    "250 m": "250 m",
    "1 km": "1 km", "500 m": "500 m",
    # confidence notes
    "Includes agricultural stubble burning but also other vegetation fires; small or short fires and fires under cloud are missed. Not yet restricted to cropland.":
        "Include arderea miriștilor, dar și alte incendii de vegetație; incendiile mici sau scurte și cele de sub nori nu sunt detectate. Încă nelimitat la terenul arabil.",
    "Model output (forced by observations), ~25 km cells; describes the area around a commune, not a single field.":
        "Rezultat de model (alimentat cu observații), celule de ~25 km; descrie zona din jurul unei comune, nu o parcelă.",
    "Satellite gravimetry: all water stored in a ~300 km region (groundwater, soil, rivers, snow) as cm of water vs the 2004–2009 mean. Shows the regional long-term trend, not a commune or field value. Typical 1σ uncertainty ≈ 2.1 cm. Gaps: GRACE ended mid-2017, GRACE-FO started mid-2018, and some single months are missing.":
        "Gravimetrie din satelit: toată apa înmagazinată într-o regiune de ~300 km (subterană, sol, râuri, zăpadă), în cm de apă față de media 2004–2009. Arată tendința regională pe termen lung, nu o valoare pentru comună sau parcelă. Incertitudine tipică 1σ ≈ 2,1 cm. Goluri: GRACE s-a încheiat la mijlocul lui 2017, GRACE-FO a început la mijlocul lui 2018 și lipsesc câteva luni.",
    "Satellite + gauge-calibrated. The Final archive ends 2025-09; Oct–Dec 2025 are not available yet (POWER precipitation covers them).":
        "Satelit calibrat cu pluviometre. Arhiva Final se oprește la 2025-09; oct–dec 2025 nu sunt încă disponibile (le acoperă precipitațiile POWER).",
    "Averaged over cropland pixels only (≥ 50 % ESA WorldCover 2021 'cropland' inside the pixel). Not available for Vâlcea county and the few communes outside the downloaded WorldCover tiles (south of 45 °N / west of 21 °E). Satellite-driven model (Penman–Monteith with MODIS vegetation); 8-day totals spread over the calendar days they cover.":
        "Medie doar pe pixelii de teren arabil (≥ 50 % „cropland” ESA WorldCover 2021 în pixel). Indisponibil pentru județul Vâlcea și pentru puținele comune din afara plăcilor WorldCover descărcate (la sud de 45 °N / la vest de 21 °E). Model bazat pe satelit (Penman–Monteith cu vegetație MODIS); totalurile pe 8 zile sunt împărțite pe zilele calendaristice acoperite.",
    "Averaged over cropland pixels only (≥ 50 % ESA WorldCover 2021 'cropland' inside the pixel). Not available for Vâlcea county and the few communes outside the downloaded WorldCover tiles (south of 45 °N / west of 21 °E). Clear-sky only (cloudy days are missing, so cloudy months are biased warm by day). Surface (skin) temperature at the ~10:30 / ~22:30 Terra overpass, not air temperature; one 8-day composite (2022-10-16) is missing.":
        "Medie doar pe pixelii de teren arabil (≥ 50 % „cropland” ESA WorldCover 2021 în pixel). Indisponibil pentru județul Vâlcea și pentru puținele comune din afara plăcilor WorldCover descărcate (la sud de 45 °N / la vest de 21 °E). Doar cer senin (zilele înnorate lipsesc, deci lunile înnorate par mai calde ziua). Temperatura suprafeței la trecerea Terra de ~10:30 / ~22:30, nu temperatura aerului; lipsește un compozit de 8 zile (2022-10-16).",
    "Averaged over cropland pixels only (≥ 50 % ESA WorldCover 2021 'cropland' inside the pixel). Not available for Vâlcea county and the few communes outside the downloaded WorldCover tiles (south of 45 °N / west of 21 °E). Good / marginal-quality pixels only; months with < 30 % clear pixels dropped. Mixes all crops: a greenness signal, not a yield estimate.":
        "Medie doar pe pixelii de teren arabil (≥ 50 % „cropland” ESA WorldCover 2021 în pixel). Indisponibil pentru județul Vâlcea și pentru puținele comune din afara plăcilor WorldCover descărcate (la sud de 45 °N / la vest de 21 °E). Doar pixeli de calitate bună / acceptabilă; lunile cu < 30 % pixeli fără nori sunt eliminate. Amestecă toate culturile: un semnal de verdeață, nu o estimare de randament.",
    "Mean over all land in the unit (forest, grassland, farmland), so in hilly / mountain units it mostly reflects forest. Good / marginal-quality pixels only; months with < 30 % clear pixels dropped.":
        "Medie pe tot terenul unității (pădure, pajiști, teren agricol), deci în zonele deluroase / montane reflectă mai ales pădurea. Doar pixeli de calitate bună / acceptabilă; lunile cu < 30 % pixeli fără nori sunt eliminate.",
    "Regional grid: neighbouring communes share the same cells, so commune values describe the surrounding region, not the commune itself. The latest months can be provisional (POWER lags real time by a few days).":
        "Grilă regională: comunele vecine împart aceleași celule, deci valorile pe comună descriu regiunea din jur, nu comuna însăși. Ultimele luni pot fi provizorii (POWER întârzie câteva zile față de timpul real).",
    "Regional grid: neighbouring communes share the same cells, so commune values describe the surrounding region, not the commune itself. 2026 (Jan–Oct) only exists for the 9 cells around Alba Iulia (roughly Alba, Sibiu and parts of the neighbouring counties).":
        "Grilă regională: comunele vecine împart aceleași celule, deci valorile pe comună descriu regiunea din jur, nu comuna însăși. Anul 2026 (ian–oct) există doar pentru cele 9 celule din jurul Alba Iuliei (aproximativ Alba, Sibiu și părți din județele vecine).",
    "Only the area around Alba Iulia was downloaded (≈ 45.6–46.5 °N, 23.0–24.2 °E), so only Alba county and nearby communes have values. One 9 km cell covers many fields, and SMAP sees only the top ~5 cm. Recommended-quality retrievals only: frozen or snow-covered ground in winter and forested mountain cells are dropped, so winter months are often empty. No SMAP data 2022-08-07 – 2022-09-19 (source gap).":
        "S-a descărcat doar zona din jurul Alba Iuliei (≈ 45,6–46,5 °N, 23,0–24,2 °E), deci doar județul Alba și comunele apropiate au valori. O celulă de 9 km acoperă multe parcele, iar SMAP vede doar primii ~5 cm. Doar măsurători de calitate recomandată: solul înghețat sau acoperit de zăpadă iarna și celulele montane împădurite sunt eliminate, deci lunile de iarnă sunt adesea goale. Fără date SMAP 2022-08-07 – 2022-09-19 (gol la sursă).",
    # derived/agro_yearly
    "Very hot days (Tmax ≥ 35 °C), Jul–Aug": "Zile foarte calde (Tmax ≥ 35 °C), iul–aug",
    "Hot days (Tmax ≥ 32 °C), Jul–Aug": "Zile caniculare (Tmax ≥ 32 °C), iul–aug",
    "Hot days (Tmax ≥ 30 °C), June": "Zile calde (Tmax ≥ 30 °C), iunie",
    "Mean Tmax, Jul–Aug": "Tmax medie, iul–aug",
    "Late frost days (Tmin < 0 °C), 15 Apr–31 May": "Zile cu îngheț târziu (Tmin < 0 °C), 15 apr–31 mai",
    "Rain, 15 May–30 Jun": "Ploaie, 15 mai–30 iun",
    "Wet days (≥ 1 mm), 15 May–30 Jun": "Zile ploioase (≥ 1 mm), 15 mai–30 iun",
    "Mean relative humidity, 15 May–30 Jun": "Umiditate relativă medie, 15 mai–30 iun",
    "Rain in July (small-grain harvest)": "Ploaie în iulie (recolta păioaselor)",
    "Rain, Sep–Oct (maize/sunflower harvest)": "Ploaie, sep–oct (recolta de porumb / floarea-soarelui)",
    "Growing-season precipitation, Apr–Sep": "Precipitații în sezonul de vegetație, apr–sep",
    "Longest dry spell (< 1 mm/day), Apr–Sep": "Cea mai lungă perioadă secetoasă (< 1 mm/zi), apr–sep",
    "Growing degree days (base 10 °C), Apr–Sep": "Grade-zile de creștere (bază 10 °C), apr–sep",
    "Evapotranspiration, Apr–Sep": "Evapotranspirație, apr–sep",
    "Water balance (rain − ET), Apr–Sep": "Bilanțul apei (ploaie − ET), apr–sep",
    "Root-zone soil moisture, Jun–Aug mean": "Umiditatea solului în zona rădăcinilor, media iun–aug",
    "Root-zone soil moisture anomaly, Jun–Aug": "Abaterea umidității solului în zona rădăcinilor, iun–aug",
    "Root-zone soil moisture anomaly, Jun–Jul": "Abaterea umidității solului în zona rădăcinilor, iun–iul",
    "Root-zone soil wetness anomaly, Jun–Aug": "Abaterea umezelii solului în zona rădăcinilor, iun–aug",
    "Root-zone soil wetness anomaly, May–Jun": "Abaterea umezelii solului în zona rădăcinilor, mai–iun",
    "From regional grids (POWER ~50 km, GLDAS ~25 km). Day counts are area-weighted averages, so they can be fractional. 2026: POWER windows only where 2026 data exist (cells around Alba Iulia); GLDAS ends 2026-07, so 2026 water-balance and summer soil-moisture values are empty.":
        "Din grile regionale (POWER ~50 km, GLDAS ~25 km). Numărul de zile e o medie ponderată pe suprafață, deci poate avea zecimale. 2026: perioadele POWER doar unde există date pentru 2026 (celulele din jurul Alba Iuliei); GLDAS se oprește la 2026-07, deci bilanțul apei și umiditatea solului de vară pentru 2026 lipsesc.",
    # derived/agro_yearly "why" (why each season indicator matters)
    "Maize flowering/grain fill: heat + drought raise pollination failure and aflatoxin risk.":
        "Înflorirea / umplerea boabelor la porumb: căldura și seceta cresc riscul de polenizare ratată și de aflatoxine.",
    "Heat stress for summer crops (maize, sunflower) during flowering and grain fill.":
        "Stres termic pentru culturile de vară (porumb, floarea-soarelui) la înflorire și umplerea boabelor.",
    "Heat at flowering of spring pulses, oats and flax (pea pod set drops above ~30 °C).":
        "Căldură la înflorirea leguminoaselor de primăvară, ovăzului și inului (la mazăre, formarea păstăilor scade peste ~30 °C).",
    "Overall summer heat load.": "Încărcarea termică totală a verii.",
    "Frost after spring sowing damages emerging spring crops (sunflower, maize, chickpea, flax).":
        "Înghețul după semănatul de primăvară afectează culturile abia răsărite (floarea-soarelui, porumb, năut, in).",
    "Wet weather at small-grain flowering (wheat, barley, oats) raises Fusarium / mycotoxin risk.":
        "Vremea umedă la înflorirea păioaselor (grâu, orz, ovăz) crește riscul de Fusarium / micotoxine.",
    "Frequent rain days during flowering favour Fusarium infection.": "Zilele ploioase dese în timpul înfloririi favorizează infecția cu Fusarium.",
    "Rain at harvest causes sprouting, quality loss and harvest delays.": "Ploaia la recoltare provoacă încolțirea, pierderi de calitate și întârzieri la recoltat.",
    "Wet harvests raise drying costs and mould / mycotoxin risk.": "Recoltele pe ploaie cresc costurile de uscare și riscul de mucegai / micotoxine.",
    "Water available to spring/summer crops.": "Apa disponibilă culturilor de primăvară / vară.",
    "Long dry spells cause drought stress, worst when they hit flowering.": "Perioadele secetoase lungi provoacă stres hidric, cel mai grav când cad la înflorire.",
    "Heat units available for warm-season crops like maize and sunflower.": "Căldura disponibilă pentru culturile iubitoare de căldură, ca porumbul și floarea-soarelui.",
    "Water used by vegetation and soil.": "Apa folosită de vegetație și sol.",
    "Negative = vegetation used more water than fell as rain (drawing down soil water).":
        "Negativ = vegetația a folosit mai multă apă decât a căzut ca ploaie (consumând apa din sol).",
    "Water in the root zone during the critical summer months.": "Apa din zona rădăcinilor în lunile critice de vară.",
    "Compared with 2015–2025 (unit mean / std): below −1 = clearly drier summer than usual.":
        "Comparat cu 2015–2025 (media / abaterea standard a unității): sub −1 = o vară clar mai secetoasă decât de obicei.",
    "Early-summer version of the Jun–Aug anomaly; exists before August, so the season forecast can use it.":
        "Varianta de început de vară a abaterii iun–aug; există înainte de august, deci prognoza sezonului o poate folosi.",
    "summer root-zone soil wetness ≥ 1 std below the 2000–2025 mean (NASA POWER)":
        "umezeala solului în zona rădăcinilor vara cu ≥ 1 abatere standard sub media 2000–2025 (NASA POWER)",
    "USDA texture class of the median clay/sand/silt": "Clasa de textură USDA a medianelor de argilă / nisip / praf",
    # crop water-need references
    "FAO_BH86 (wheat value; FAO-56 groups barley, oats and wheat)": "FAO_BH86 (valoarea grâului; FAO-56 grupează orzul, ovăzul și grâul)",
    "approx (not in FAO_BH86; drought-tolerant pulse, FAO56 Kc 1.00 × short season)":
        "aprox. (nu e în FAO_BH86; leguminoasă rezistentă la secetă, FAO56 Kc 1,00 × sezon scurt)",
    "approx (not in FAO_BH86; FAO56 Kc 1.10)": "aprox. (nu e în FAO_BH86; FAO56 Kc 1,10)",
    # soil
    "Soil organic carbon": "Carbon organic în sol",
    "pH (water)": "pH (în apă)",
    "Clay": "Argilă", "Sand": "Nisip", "Silt": "Praf",
    "Total nitrogen": "Azot total",
    "Bulk density": "Densitate aparentă",
    "Cation exchange capacity": "Capacitate de schimb cationic",
    "0–30 cm, depth-weighted (0–5, 5–15, 15–30 cm)": "0–30 cm, ponderat pe adâncime (0–5, 5–15, 15–30 cm)",
    "median and 10th–90th percentile of pixels in the unit (water/urban excluded)":
        "mediana și percentilele 10–90 ale pixelilor din unitate (fără apă / zone construite)",
    "Modelled soil map (machine learning on soil profiles), not field measurements. Good for comparing areas; a lab test is needed for a specific field.":
        "Hartă de sol modelată (învățare automată pe profiluri de sol), nu măsurători din câmp. Bună pentru comparat zone; pentru o anumită parcelă e nevoie de o analiză de laborator.",
    # INS / cropmap / terrain
    "Cultivated area (ha)": "Suprafață cultivată (ha)",
    "Production (t)": "Producție (t)",
    "Average yield (kg/ha)": "Randament mediu (kg/ha)",
    "Official statistics, county level only. The latest year may be provisional. Commune views show their county's figures.":
        "Statistici oficiale, doar la nivel de județ. Ultimul an poate fi provizoriu. Comunele arată cifrele județului lor.",
    "INS does not report chickpea separately (it is inside 'grain legumes').": "INS nu raportează năutul separat (e inclus în „leguminoase boabe”).",
    "Satellite classification (Sentinel-1); individual fields can be misclassified, totals are indicative. Two snapshots only, not a yearly series.":
        "Clasificare din satelit (Sentinel-1); parcelele individuale pot fi clasificate greșit, totalurile sunt orientative. Doar două momente, nu o serie anuală.",
    "Only units covered ≥ 95% by the downloaded tiles are listed (terrain: 22–25 °E × 45–47 °N; land cover: 21–27 °E × 45–48 °N). Slope is in percent (rise / run × 100) from the 30 m SRTM DEM; cropland = WorldCover class 40. Above ~10 % slope, water erosion on bare soil rises steeply, so steep cropland benefits most from winter cover and contour work.":
        "Sunt listate doar unitățile acoperite ≥ 95% de plăcile descărcate (relief: 22–25 °E × 45–47 °N; acoperire: 21–27 °E × 45–48 °N). Panta e în procente (diferență de nivel / distanță × 100) din modelul SRTM de 30 m; teren arabil = clasa WorldCover 40. Peste ~10 % pantă, eroziunea solului descoperit crește brusc, deci terenul arabil în pantă câștigă cel mai mult din culturile de toamnă și lucrările pe curba de nivel.",
    # crop traits (sensitive stages, quality notes, planner labels)
    "flowering / silking": "înflorire / mătăsire",
    "flowering (anthesis)": "înflorire (anteză)",
    "flowering (panicle)": "înflorire (panicul)",
    "flowering / pod set": "înflorire / formarea păstăilor",
    "flowering / pod fill": "înflorire / umplerea păstăilor",
    "flowering / seed fill": "înflorire / umplerea semințelor",
    "flowering": "înflorire",
    "Heat + drought at flowering raise aflatoxin risk; wet harvest raises mould risk.":
        "Căldura și seceta la înflorire cresc riscul de aflatoxine; recolta pe ploaie crește riscul de mucegai.",
    "Wet, humid flowering raises Fusarium head blight / DON mycotoxin risk; rain at harvest lowers quality.":
        "Înflorirea pe vreme umedă crește riscul de fuzarioză a spicului / micotoxina DON; ploaia la recoltare scade calitatea.",
    "Wet flowering raises Fusarium / mycotoxin risk; rain at harvest causes sprouting.":
        "Înflorirea pe vreme umedă crește riscul de Fusarium / micotoxine; ploaia la recoltare provoacă încolțirea.",
    "Wet flowering raises Fusarium / mycotoxin risk; oats tolerate acid soils better than other cereals.":
        "Înflorirea pe vreme umedă crește riscul de Fusarium / micotoxine; ovăzul tolerează solurile acide mai bine decât alte cereale.",
    "Heat (> ~30 °C) and drought at flowering cut pod set; rain at harvest lowers seed quality.":
        "Căldura (> ~30 °C) și seceta la înflorire reduc formarea păstăilor; ploaia la recoltare scade calitatea boabelor.",
    "Wet, humid weather favours Ascochyta blight; late frost damages seedlings.":
        "Vremea umedă favorizează antracnoza (Ascochyta); înghețul târziu afectează răsadurile.",
    "Drought at pod fill cuts yield and protein; wet harvest lowers quality.":
        "Seceta la umplerea păstăilor reduce randamentul și proteina; recolta pe ploaie scade calitatea.",
    "Deep roots make it drought-tolerant, but heat at flowering lowers oil content; wet late summer favours Sclerotinia head rot.":
        "Rădăcinile adânci o fac rezistentă la secetă, dar căldura la înflorire scade conținutul de ulei; sfârșitul de vară umed favorizează putregaiul alb al calatidiului (Sclerotinia).",
    "Heat and drought at flowering lower seed set and oil content.": "Căldura și seceta la înflorire reduc legarea semințelor și conținutul de ulei.",
    "No Romanian county statistics for chickpea; yield uses INS 'grain legumes' as a proxy (low confidence).":
        "Nu există statistici pe județ pentru năut; randamentul folosește „leguminoase boabe” INS ca aproximare (încredere scăzută).",
    "Oil flax is grown on very small areas in the region; INS figures are sparse.": "Inul pentru ulei se cultivă pe suprafețe foarte mici în regiune; cifrele INS sunt rare.",
    "early (FAO 300)": "timpuriu (FAO 300)", "medium (FAO 400)": "semitimpuriu (FAO 400)", "late (FAO 500)": "târziu (FAO 500)",
    "early (MG 00)": "timpuriu (MG 00)", "medium (MG 0)": "mijlociu (MG 0)", "late (MG I)": "târziu (MG I)",
    "Hand-curated literature values for Transylvanian conditions. Ranges, not measurements. Values marked 'approx' are approximate thresholds from agronomic literature and carry lower confidence. Refine with a local agronomist.":
        "Valori din literatură, alese manual pentru condițiile din Transilvania. Intervale, nu măsurători. Valorile marcate „approx” sunt praguri aproximative din literatura agronomică și au încredere mai mică. De rafinat cu un agronom local.",
    "Cereal after a grain legume: +10% yield (conservative; reported pre-crop effects are often 0.5–1.6 t/ha for wheat).":
        "Cereală după o leguminoasă boabe: +10% randament (prudent; efectele raportate ale premergătoarei sunt adesea 0,5–1,6 t/ha la grâu).",
    "Same crop in consecutive years: −10% yield (continuous-maize penalty used for all crops).":
        "Aceeași cultură în ani consecutivi: −10% randament (penalizarea porumbului după porumb, folosită pentru toate culturile).",
    # planner methods (routers/planner.py)
    "Sowing, maturity and harvest timing: NASA POWER daily weather 2000–2026 for the county (frost dates, 7-day mean temperature, heat sums above 10 °C).":
        "Momentul semănatului, maturității și recoltei: vremea zilnică NASA POWER 2000–2026 pentru județ (date de îngheț, temperatura medie pe 7 zile, sume de căldură peste 10 °C).",
    "Yield: county trend from INS yields 2000–2025 (ranges = how far real years fell from the trend), × your field's own level learned from your reports, × previous-crop effect.":
        "Randament: tendința județului din randamentele INS 2000–2025 (intervale = cât de departe au căzut anii reali față de tendință), × nivelul propriu al parcelei învățat din rapoartele dvs., × efectul culturii premergătoare.",
    "Rotation choice: the dashboard's rotation score (yield, water, soil, risk) with your weights; every allowed sequence is checked.":
        "Alegerea rotației: scorul de rotație al panoului (randament, apă, sol, risc) cu ponderile dvs.; fiecare succesiune permisă e verificată.",
    "Rotation effects (after legume, repeated crop) start from literature values and move toward what farmers report as reports accumulate.":
        "Efectele rotației (după leguminoasă, cultură repetată) pornesc de la valori din literatură și se apropie de ce raportează fermierii pe măsură ce se adună rapoarte.",
    "Seed rates, maturity heat sums and sowing temperatures are approximate agronomy values; confirm with your seed supplier.":
        "Normele de sămânță, sumele de căldură până la maturitate și temperaturile de semănat sunt valori agronomice aproximative; confirmați cu furnizorul de semințe.",
    "Growing-season rain only (Apr–Sep). The FAO water need is the crop's total use; the rest comes from water stored in the soil over winter (deep-rooted and winter crops use it most) or irrigation.":
        "Doar ploaia din sezonul de vegetație (apr–sep). Necesarul FAO e consumul total al culturii; restul vine din apa înmagazinată în sol peste iarnă (o folosesc mai ales culturile cu rădăcini adânci și cele de toamnă) sau din irigații.",
    # drawn fields (field/coarse.py, field/imagery.py)
    "Rain measured from satellites (calibrated with gauges).": "Ploaie măsurată din satelit (calibrată cu pluviometre).",
    "Rain from the POWER reanalysis model (coarser; also covers months IMERG lacks).": "Ploaie din modelul de reanaliză POWER (mai grosier; acoperă și lunile care lipsesc din IMERG).",
    "Average daily maximum air temperature.": "Temperatura maximă zilnică medie a aerului.",
    "Days with maximum temperature ≥ 32 °C.": "Zile cu temperatura maximă ≥ 32 °C.",
    "Water in the top 1 m of soil, from the GLDAS land model.": "Apa din primul metru de sol, din modelul de suprafață GLDAS.",
    "pixel centres inside the field": "centrele pixelilor în interiorul parcelei",
    "pixels touching the field (the field is smaller than one pixel)": "pixelii care ating parcela (parcela e mai mică decât un pixel)",
    "pixels touching the field (field smaller than one pixel)": "pixelii care ating parcela (parcela e mai mică decât un pixel)",
    "SoilGrids rasters are not on this server; see the commune soil values.": "Rasterele SoilGrids nu sunt pe acest server; vedeți valorile de sol ale comunei.",
    "SoilGrids has no prediction for these pixels (usually built-up land or water).": "SoilGrids nu are predicție pentru acești pixeli (de obicei zone construite sau apă).",
    "A prediction from a global soil model, not a measurement of your field. Fields smaller than one pixel get that pixel's value. Take soil samples for decisions on liming or fertiliser.":
        "O predicție dintr-un model global de sol, nu o măsurătoare a parcelei dvs. Parcelele mai mici decât un pixel primesc valoarea acelui pixel. Pentru decizii de amendare sau fertilizare luați probe de sol.",
    "ISRIC SoilGrids 2.0 (CC BY 4.0), predicted mean, 0–30 cm depth-weighted": "ISRIC SoilGrids 2.0 (CC BY 4.0), medie prezisă, 0–30 cm ponderat pe adâncime",
    "SMAP was only processed for communes around Alba Iulia; none for this commune.": "SMAP a fost procesat doar pentru comunele din jurul Alba Iuliei; nu și pentru această comună.",
    "Average over the commune of 9 km SMAP cells (surface ~5 cm). It cannot show differences between fields.":
        "Medie pe comună a celulelor SMAP de 9 km (suprafață ~5 cm). Nu poate arăta diferențe între parcele.",
    "NASA HLS v2.0 — Harmonized Landsat 8/9 + Sentinel-2 (LP DAAC)": "NASA HLS v2.0 — Landsat 8/9 + Sentinel-2 armonizate (LP DAAC)",
    "Fmask (cloud, cloud shadow, adjacent, snow masked)": "Fmask (nori, umbre de nori, zone adiacente și zăpadă mascate)",
    "Copernicus Sentinel-2 L2A (ESA), via Element 84 Earth Search on AWS": "Copernicus Sentinel-2 L2A (ESA), prin Element 84 Earth Search pe AWS",
    "Scene classification (SCL): only vegetation, bare soil, water kept": "Clasificarea scenei (SCL): se păstrează doar vegetația, solul gol și apa",
    "No Earthdata login configured on the server (~/.netrc or S2F_EARTHDATA_TOKEN).": "Pe server nu e configurată autentificarea Earthdata (~/.netrc sau S2F_EARTHDATA_TOKEN).",
    "Catalogue search failed; try again later.": "Căutarea în catalog a eșuat; încercați din nou mai târziu.",
    "Could not load imagery for this field. Try again in a minute.": "Imaginile pentru această parcelă nu au putut fi încărcate. Încercați din nou peste un minut.",
    "06-01 – 07-31": "01.06 – 31.07",
    # routers: errors shown to the user
    "Too many requests, please wait a moment": "Prea multe cereri, vă rog așteptați puțin",
    "Too many searches, please wait a moment": "Prea multe căutări, vă rog așteptați puțin",
    "Place search is not available right now": "Căutarea locurilor nu este disponibilă acum",
    "Type at least 2 characters": "Scrieți cel puțin 2 caractere",
    "Too many changes, please wait a moment": "Prea multe modificări, vă rog așteptați puțin",
    "Too many saved fields; delete some first": "Prea multe parcele salvate; ștergeți câteva întâi",
    "Field not found": "Parcela nu a fost găsită",
    "Report not found": "Raportul nu a fost găsit",
    "Unknown or expired job; start it again": "Lucrare necunoscută sau expirată; porniți-o din nou",
    "This field is outside the study area (Alba and neighbouring counties)": "Această parcelă e în afara zonei de studiu (Alba și județele vecine)",
}

_IDENT = re.compile(r"^[a-z0-9_.\-]+$")


def L(s: Any) -> Any:
    """Translate one fixed display string (no-op in English or when unknown)."""
    if not ro() or not isinstance(s, str) or not s:
        return s
    hit = STATIC.get(s)
    if hit is not None:
        return hit
    if _WINDOW_RE.match(s):
        return months(s)
    return s


def localize(obj: Any) -> Any:
    """Copy of a JSON-like object with fixed display strings translated (identifiers kept)."""
    if not ro():
        return obj

    def walk(o: Any) -> Any:
        if isinstance(o, str):
            if _IDENT.match(o) and o not in STATIC:
                return o
            return L(o)
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o

    return walk(obj)
