"""Procurement view (requirements 7–9): per county, for one ingredient crop.

availability – how much is produced and how reliably (INS + climate hazards)
quality      – how often weather hit the crop's quality-sensitive windows
impact       – water need vs dry-year rain, field N2O emissions per tonne
Plus rule-based recommendations; each lists the numbers that triggered it.
"""

from __future__ import annotations

import statistics
from typing import Any

from .hazards import HAZARDS, clean, crop_hazard_keys, cv, hazard_years, median, percentile

GROUPS = {
    "protein": ["pea", "soy", "chickpea"],
    "energy": ["maize", "barley", "oats"],
    "oil": ["sunflower", "flax"],
}
AREA_CROPS = ["maize", "wheat", "barley", "oats", "sunflower", "soy", "rapeseed", "pea", "flax"]
PEA_PROTEIN = (0.21, 0.25)  # protein share of dry pea seed (literature range)


def _proxy(crop: str) -> str:
    return "grain_legumes" if crop == "chickpea" else crop


def _slope_pct(xs: list) -> float | None:
    pts = [(i, x) for i, x in enumerate(xs) if x is not None and x > 0]
    if len(pts) < 4:
        return None
    mx = statistics.mean(i for i, _ in pts)
    my = statistics.mean(x for _, x in pts)
    num = sum((i - mx) * (x - my) for i, x in pts)
    den = sum((i - mx) ** 2 for i, _ in pts)
    return (num / den) / my * 100 if den and my else None


def _corr(a: list, b: list) -> float | None:
    pts = [(x, y) for x, y in zip(a, b) if x and y]
    if len(pts) < 5:
        return None
    xs, ys = zip(*pts)
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


NDVI_MONTHS = (4, 5, 6, 7, 8)  # main growing season of the study area's arable crops


def vegetation_signal(keys: list[str], vals: list | None) -> dict[str, Any] | None:
    """Apr–Aug mean cropland NDVI per year; latest full season vs the mean of the earlier ones.

    All cropland together (MODIS cannot tell crops apart at 1 km), so it is context for
    availability, not a crop-specific yield estimate. A season needs all five months."""
    if not vals:
        return None
    by: dict[int, list[float]] = {}
    for k, v in zip(keys, vals):
        if v is not None and int(k[5:7]) in NDVI_MONTHS:
            by.setdefault(int(k[:4]), []).append(v)
    seasons = {y: sum(v) / len(v) for y, v in by.items() if len(v) == len(NDVI_MONTHS)}
    if len(seasons) < 3:
        return None
    last = max(seasons)
    base_years = [y for y in seasons if y != last]
    base = sum(seasons[y] for y in base_years) / len(base_years)
    return {
        "year": last, "ndvi": round(seasons[last], 3), "baseline": round(base, 3),
        "baseline_years": [min(base_years), max(base_years)],
        "vs_baseline_pct": round(100 * (seasons[last] / base - 1), 1),
        "seasons": {str(y): round(v, 3) for y, v in sorted(seasons.items())},
    }


def county_metrics(crop: str, code: str, ins_c: dict, agro: dict, traits: dict, fires: list | None,
                   ndvi: dict | None = None) -> dict[str, Any]:
    t = traits["crops"][crop]
    A = traits["assumptions"]
    rec = ins_c.get(_proxy(crop)) or {}
    prod, area, yld = rec.get("production_t") or [], rec.get("area_ha") or [], rec.get("yield_kg_ha") or []
    years = agro["years"]
    recent = prod[-5:]
    prod_med = median(recent)
    hist_med = median(prod[:-1])
    latest = prod[-1] if prod else None
    ycv = cv(yld)  # weather-driven swing; production also moves with farmers' area decisions

    hk = crop_hazard_keys(t)
    hy = hazard_years(hk, agro["values"], years)
    valid = [y for y in years if any((agro["values"].get(k) or [None] * len(years))[years.index(y)] is not None for k in hk)]
    bad = [y for y in valid if hy[y]]
    freq = len(bad) / len(valid) if valid else None
    last_year = max(valid) if valid else None
    latest_hits = hy.get(last_year, []) if last_year else []

    avail = _clamp(100 * (1 - 0.5 * min(1.0, (ycv if ycv is not None else 0.3) / 0.4) - 0.5 * (freq if freq is not None else 0.5)))
    quality = _clamp(100 * (1 - (freq if freq is not None else 0.5)))

    precip = agro["values"].get("precip_apr_sep") or []
    dry = percentile(precip, 0.2)
    need = sum(t["water_need_mm"]) / 2
    water_score = _clamp(100 * min(1.0, dry / need)) if dry else None
    yld_med = median(yld[-5:])
    n_mid = sum(t["n_fert_kg_ha"]) / 2
    ef = A["n2o_ef1"]["value"] * A["n2o_n_to_n2o"]["value"] * A["n2o_gwp100"]["value"]  # kg CO2e per kg N
    em = (n_mid * ef) / (yld_med / 1000) if yld_med else None  # kg CO2e per t
    em_score = _clamp(100 * (1 - min(1.0, em / 400))) if em is not None else None
    parts = [s for s in (water_score, em_score) if s is not None]
    impact = sum(parts) / len(parts) if parts else None

    tracked = sum(((ins_c.get(c) or {}).get("area_ha") or [0])[-1] or 0 for c in AREA_CROPS)
    legume_area = sum(((ins_c.get(c) or {}).get("area_ha") or [0])[-1] or 0 for c in ("pea", "soy"))
    fires_yr = (sum(f for f in fires if f) / (len(fires) / 12)) if fires else None

    conf = "high" if (prod_med or 0) >= 1000 else ("medium" if (prod_med or 0) >= 100 else "low")
    if crop == "chickpea":
        conf = "low"

    return {
        "availability": {
            "score": round(avail), "production_t_median_5y": prod_med, "latest_t": latest,
            "latest_vs_median_pct": round((latest / hist_med - 1) * 100) if latest and hist_med else None,
            "area_ha_latest": area[-1] if area else None, "area_trend_pct_yr": round(_slope_pct(area), 1) if _slope_pct(area) is not None else None,
            "yield_cv": round(ycv, 2) if ycv is not None else None, "hazard_years": len(bad), "years": len(valid),
            # INS years start with the agro years (2015) but end earlier (agro has 2026 where POWER has it)
            "series": {"years": years[:len(prod)], "production_t": prod, "area_ha": area, "yield_kg_ha": yld},
            "vegetation": vegetation_signal(ndvi["keys"], ndvi["units"].get(code)) if ndvi else None,
        },
        "quality": {
            "score": round(quality), "hazard_freq": round(freq, 2) if freq is not None else None,
            "bad_years": {y: hy[y] for y in bad}, "latest_year": last_year, "latest_hits": latest_hits,
        },
        "impact": {
            "score": round(impact) if impact is not None else None, "water_score": round(water_score) if water_score is not None else None,
            "water_need_mm": t["water_need_mm"], "dry_year_rain_mm": round(dry) if dry else None,
            "emissions_kg_co2e_t": round(em) if em is not None else None, "yield_kg_ha_5y": yld_med,
            "legume_share_pct": round(100 * legume_area / tracked, 1) if tracked else None,
            "fires_per_1000ha_yr": round(1000 * fires_yr / tracked, 2) if fires_yr is not None and tracked else None,
        },
        "confidence": conf,
    }


def procurement(crop: str, counties: dict[str, str], ins: dict, agro_all: dict, traits: dict,
                fires_all: dict, ndvi: dict | None = None, outlook: dict | None = None) -> dict[str, Any]:
    if crop not in traits["crops"]:
        raise ValueError(f"unknown crop {crop}")
    out = {}
    for code, name in counties.items():
        agro = {"years": agro_all["years"], "values": agro_all["units"].get(code, {})}
        m = county_metrics(crop, code, ins["counties"].get(code, {}), agro, traits, fires_all.get(code), ndvi)
        out[code] = {"name": name, **m}

    recs = recommendations(crop, out, ins, agro_all, traits, counties)
    if outlook:
        recs = outlook_recs(crop, outlook, counties) + recs
    t = traits["crops"][crop]
    return {
        "crop": crop,
        "proxy": _proxy(crop) if crop == "chickpea" else None,
        "counties": out,
        "recommendations": recs,
        "outlook": outlook,
        "assumptions": [
            "Availability = 100 × (1 − 0.5 × min(1, yield CV / 40%) − 0.5 × share of hazard years); production volume is shown alongside.",
            "Quality = 100 × (1 − share of years in which the crop's sensitive window was hit; 2015–2025, plus 2026 where NASA POWER has 2026 data).",
            "Cropland greenness = Apr–Aug mean MODIS NDVI over cropland pixels, latest season vs the mean of the earlier seasons (2022 onward). All crops together; shown as context, not part of the scores.",
            "Hazard thresholds: " + "; ".join(HAZARDS[k].text for k in crop_hazard_keys(t)) + ".",
            "Impact = mean of water score (dry-year Apr–Sep rain ÷ crop water need) and emissions score (100 at 0, 0 at ≥ 400 kg CO2e/t).",
            f"Emissions are field N2O only: mid-range N fertiliser ({t['n_fert_kg_ha'][0]}–{t['n_fert_kg_ha'][1]} kg N/ha) × IPCC EF1 1% × 44/28 × GWP100 273 ÷ 5-year median yield. Fertiliser manufacture, fuel and transport are not included.",
        ],
        "sources": [
            "INS TEMPO AGR108A/109A/110A (area, production, yield), county level",
            "NASA POWER daily and NASA GLDAS Noah monthly (hazard years, rain)",
            "NASA FIRMS VIIRS (vegetation fires)",
            "NASA MODIS MOD13A3 NDVI on ESA WorldCover 2021 cropland (season greenness)",
            "Crop traits: FAO (Brouwer & Heibloem 1986; FAO-56), IPCC 2019, AR6",
        ],
    }


def recommendations(crop: str, data: dict, ins: dict, agro_all: dict, traits: dict, counties: dict) -> list[dict]:
    recs = []
    prod = {c: d["availability"]["production_t_median_5y"] or 0 for c, d in data.items()}
    total = sum(prod.values())
    if total <= 0:
        return [{"type": "data", "title": "Not enough production data",
                 "text": f"INS reports too little {crop} production in these counties to rank sourcing areas.", "numbers": {}}]

    # 1. Spread purchases across reliable, weakly correlated counties
    cand = [c for c in data if prod[c] / total >= 0.05]
    cand.sort(key=lambda c: -(data[c]["availability"]["score"] + data[c]["quality"]["score"]))
    if len(cand) >= 2:
        best = None
        top = cand[:4]
        for i, a in enumerate(top):
            for b in top[i + 1:]:
                r = _corr(data[a]["availability"]["series"]["yield_kg_ha"], data[b]["availability"]["series"]["yield_kg_ha"])
                if r is not None and (best is None or r < best[2]):
                    best = (a, b, r)
        if best:
            a, b, r = best
            recs.append({
                "type": "spread", "title": "Split purchases between two reliable counties",
                "text": f"Source {crop} from {counties[a]} and {counties[b]}: both score well on availability and quality, and their yields moved together only weakly (r = {r:.2f}, 2015–2025), so a bad year in one is less likely to hit the other.",
                "numbers": {"counties": [a, b], "yield_correlation": round(r, 2),
                            "share_of_region_pct": round(100 * (prod[a] + prod[b]) / total)},
            })

    # 2. This season's quality alerts, grouped by season and hazard. The latest season with
    # weather data differs by county (2026 only where NASA POWER 2026 data were downloaded).
    hit = {c: d["quality"]["latest_hits"] for c, d in data.items() if d["quality"]["latest_hits"] and prod[c] > 0}
    if hit:
        by_year: dict[int, dict[str, list[str]]] = {}
        for c, ks in hit.items():
            yr = data[c]["quality"]["latest_year"]
            for k in ks:
                by_year.setdefault(yr, {}).setdefault(k, []).append(counties[c])
        segs = []
        for yr in sorted(by_year, reverse=True):
            n_yr = sum(1 for d in data.values() if d["quality"]["latest_year"] == yr)
            parts = [f"{HAZARDS[k].text}: {', '.join(cs) if len(cs) < n_yr else 'all counties with ' + str(yr) + ' data'}"
                     for k, cs in sorted(by_year[yr].items(), key=lambda x: -len(x[1]))]
            segs.append(f"In {yr} the {crop} sensitive period was hit — " + "; ".join(parts) + ".")
        latest = {c: d["quality"]["latest_year"] for c, d in data.items() if d["quality"]["latest_year"]}
        note = ""
        if len(set(latest.values())) > 1:
            newest = max(latest.values())
            have = [counties[c] for c, y in latest.items() if y == newest]
            note = f" {newest} weather data exist only for {', '.join(have)}; the other counties show their latest season ({min(latest.values())})."
        years_txt = "/".join(str(y) for y in sorted(by_year, reverse=True))
        recs.append({
            "type": "quality", "title": f"Check {years_txt} lots for weather-related quality problems",
            "text": " ".join(segs) + " " + traits["crops"][crop]["sensitive"]["quality"]
                    + " Test incoming lots (e.g. mycotoxins) before blending." + note,
            "numbers": {"counties": list(hit), "by_year_hazard": {str(y): v for y, v in by_year.items()}},
        })

    # 3. Alternative ingredient in the same functional group
    group = next((g for g, cs in GROUPS.items() if crop in cs), None)
    if group:
        def region_score(c: str) -> float | None:
            vals = []
            for code in counties:
                agro = {"years": agro_all["years"], "values": agro_all["units"].get(code, {})}
                m = county_metrics(c, code, ins["counties"].get(code, {}), agro, traits, None)
                if (m["availability"]["production_t_median_5y"] or 0) > 0:
                    vals.append((m["availability"]["score"] + m["quality"]["score"]) / 2)
            return sum(vals) / len(vals) if vals else None

        mine = region_score(crop)
        # chickpea has only proxy statistics, so it is never proposed as an alternative
        alts = [(c, region_score(c)) for c in GROUPS[group] if c not in (crop, "chickpea")]
        alts = [(c, s) for c, s in alts if s is not None and mine is not None and s >= mine + 5]
        if alts:
            c, s = max(alts, key=lambda x: x[1])
            recs.append({
                "type": "alternative", "title": f"Consider {c} as a partial substitute",
                "text": f"In this region {c} scores {s:.0f} on availability + quality versus {mine:.0f} for {crop} ({group} ingredient group). Test it in recipes as a partial replacement to spread weather risk.",
                "numbers": {"alternative": c, "alt_score": round(s), "crop_score": round(mine)},
            })

    # 4. Impact estimate: a quarter of suppliers add pea to their rotation
    t = traits["crops"][crop]
    if not t["legume"]:
        area = sum(((ins["counties"].get(c, {}).get(crop) or {}).get("area_ha") or [0])[-1] or 0 for c in counties)
        pea_y = median([median((ins["counties"].get(c, {}).get("pea") or {}).get("yield_kg_ha") or []) for c in counties
                        if median((ins["counties"].get(c, {}).get("pea") or {}).get("yield_kg_ha") or [])])
        if area and pea_y:
            ha = area * 0.25 / 4  # one year in four, on a quarter of the area
            dn = (sum(t["n_fert_kg_ha"]) / 2 - sum(traits["crops"]["pea"]["n_fert_kg_ha"]) / 2) * ha
            A = traits["assumptions"]
            co2 = dn * A["n2o_ef1"]["value"] * A["n2o_n_to_n2o"]["value"] * A["n2o_gwp100"]["value"] / 1000
            pea_t = ha * pea_y / 1000
            recs.append({
                "type": "contract", "title": "Contract farmers who add pea to their rotation",
                "text": (f"If a quarter of the {crop} area in these counties ({area:,.0f} ha in the latest year) grew pea one year in four, "
                         f"about {ha:,.0f} ha/yr would be pea: ≈ {pea_t:,.0f} t pea (≈ {pea_t * PEA_PROTEIN[0]:,.0f}–{pea_t * PEA_PROTEIN[1]:,.0f} t protein), "
                         f"≈ {dn / 1000:,.0f} t less fertiliser N and ≈ {co2:,.0f} t CO2e less field N2O per year, plus a yield bonus for the following cereal. "
                         "Offer contracts or premiums to these farmers."),
                "numbers": {"area_ha": area, "pea_ha_per_year": round(ha), "pea_t": round(pea_t), "n_saved_t": round(dn / 1000, 1), "co2e_saved_t": round(co2)},
                "assumptions": [
                    "25% of the crop's area, pea once in a 4-year rotation (replaces this crop that year).",
                    "Pea yield = median county pea yield 2015–2025 (INS); protein 21–25% of dry seed.",
                    "Fertiliser N: mid-range of crop traits; N2O via IPCC EF1 1%, GWP100 273. Estimate only.",
                ],
            })
    return recs


def outlook_recs(crop: str, outlook: dict, counties: dict) -> list[dict]:
    """Idea 5: turn the season yield outlook into a buying signal (only from reliable models)."""
    reg = outlook.get("region")
    if not reg:
        return []
    fc = {c: outlook["counties"][c]["forecast"] for c in reg["counties"]}
    pct = round(100 * (reg["production_t"] / reg["normal_t"] - 1)) if reg["normal_t"] else None
    low = [counties[c] for c, f in fc.items() if f["supply"]["vs_normal_pct"] <= -10]
    names = "the 8 study counties" if len(reg["counties"]) == len(counties) else ", ".join(counties[c] for c in reg["counties"])
    if pct is not None and pct <= -10:
        title = f"Expect less {crop} from {names} in {reg['year']}"
        action = "Secure volume early or shift part of the purchase to other counties / an alternative ingredient."
    elif pct is not None and pct >= 10:
        title = f"Good {reg['year']} {crop} outlook in {names}"
        action = "A good moment to contract volume from these counties."
    else:
        title = f"Normal {reg['year']} {crop} outlook in {names}"
        action = "No change to the buying plan needed from the weather signal."
    drivers = sorted((x for f in fc.values() for x in f["contributions"]), key=lambda x: x["effect_pct"])
    worst = drivers[0] if drivers and drivers[0]["effect_pct"] < -3 else None
    sig = "" if reg.get("signal") == "strong" else " The weather signal is weak (the model beats a trend-only guess by only 5–10 %), so treat this as a hint."
    return [{
        "type": "outlook", "title": title,
        "text": (f"Weather-based forecast for {names}: about {reg['production_t']:,} t "
                 f"(likely {reg['low_t']:,}–{reg['high_t']:,} t) vs {reg['normal_t']:,} t in a normal year ({pct:+d} %)."
                 + (f" Main drag: {worst['label']} ({worst['effect_pct']:+.0f} %)." if worst else "")
                 + (f" Weakest: {', '.join(low)}." if low and len(low) < len(fc) else "") + " " + action
                 + sig),
        "numbers": {"region": reg},
        "assumptions": outlook["method"][-2:],
    }]
