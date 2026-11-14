"""Procurement view (requirements 7–9): per county, for one ingredient crop.

availability – how much is produced and how reliably (INS + climate hazards)
quality      – how often weather hit the crop's quality-sensitive windows
impact       – water need vs dry-year rain, field N2O emissions per tonne
Plus rule-based recommendations; each lists the numbers that triggered it.
"""

from __future__ import annotations

import statistics
from typing import Any

from .. import i18n as I
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
            I.t("pr_a_avail"),
            I.t("pr_a_quality"),
            I.t("pr_a_ndvi"),
            I.t("f_thresholds", list="; ".join(HAZARDS[k].text for k in crop_hazard_keys(t))),
            I.t("pr_a_impact"),
            I.t("pr_a_emis", lo=t["n_fert_kg_ha"][0], hi=t["n_fert_kg_ha"][1]),
        ],
        "sources": [I.t(k) for k in ("pr_s_ins", "pr_s_weather", "pr_s_fires", "pr_s_ndvi", "pr_s_traits")],
    }


def recommendations(crop: str, data: dict, ins: dict, agro_all: dict, traits: dict, counties: dict) -> list[dict]:
    recs = []
    prod = {c: d["availability"]["production_t_median_5y"] or 0 for c, d in data.items()}
    total = sum(prod.values())
    if total <= 0:
        return [{"type": "data", "title": I.t("pr_nodata_title"),
                 "text": I.t("pr_nodata_text", crop=I.crop(crop)), "numbers": {}}]

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
                "type": "spread", "title": I.t("pr_spread_title"),
                "text": I.t("pr_spread_text", crop=I.crop(crop), a=counties[a], b=counties[b], r=I.num(r, 2)),
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
            parts = [f"{HAZARDS[k].text}: {', '.join(cs) if len(cs) < n_yr else I.t('pr_q_all', y=yr)}"
                     for k, cs in sorted(by_year[yr].items(), key=lambda x: -len(x[1]))]
            segs.append(I.t("pr_q_seg", y=yr, crop=I.crop(crop), parts="; ".join(parts)))
        latest = {c: d["quality"]["latest_year"] for c, d in data.items() if d["quality"]["latest_year"]}
        note = ""
        if len(set(latest.values())) > 1:
            newest = max(latest.values())
            have = [counties[c] for c, y in latest.items() if y == newest]
            note = I.t("pr_q_note", y=newest, have=", ".join(have), old=min(latest.values()))
        years_txt = "/".join(str(y) for y in sorted(by_year, reverse=True))
        recs.append({
            "type": "quality", "title": I.t("pr_q_title", years=years_txt),
            "text": " ".join(segs) + " " + I.L(traits["crops"][crop]["sensitive"]["quality"])
                    + I.t("pr_q_test") + note,
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
                "type": "alternative", "title": I.t("pr_alt_title", alt=I.crop(c)),
                "text": I.t("pr_alt_text", alt=I.crop(c), s=f"{s:.0f}", m=f"{mine:.0f}", crop=I.crop(crop), group=I.t(f"pr_group_{group}")),
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
                "type": "contract", "title": I.t("pr_contract_title"),
                "text": I.t("pr_contract_text", crop=I.crop(crop), area=I.num(area), ha=I.num(ha), pea_t=I.num(pea_t),
                            p_lo=I.num(pea_t * PEA_PROTEIN[0]), p_hi=I.num(pea_t * PEA_PROTEIN[1]), n_t=I.num(dn / 1000), co2=I.num(co2)),
                "numbers": {"area_ha": area, "pea_ha_per_year": round(ha), "pea_t": round(pea_t), "n_saved_t": round(dn / 1000, 1), "co2e_saved_t": round(co2)},
                "assumptions": [I.t("pr_contract_a1"), I.t("pr_contract_a2"), I.t("pr_contract_a3")],
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
    names = I.t("pr_o_names_all") if len(reg["counties"]) == len(counties) else ", ".join(counties[c] for c in reg["counties"])
    cn = I.crop(crop)
    if pct is not None and pct <= -10:
        title = I.t("pr_o_low_title", crop=cn, names=names, y=reg["year"])
        action = I.t("pr_o_low_action")
    elif pct is not None and pct >= 10:
        title = I.t("pr_o_good_title", crop=cn, names=names, y=reg["year"])
        action = I.t("pr_o_good_action")
    else:
        title = I.t("pr_o_norm_title", crop=cn, names=names, y=reg["year"])
        action = I.t("pr_o_norm_action")
    drivers = sorted((x for f in fc.values() for x in f["contributions"]), key=lambda x: x["effect_pct"])
    worst = drivers[0] if drivers and drivers[0]["effect_pct"] < -3 else None
    sig = "" if reg.get("signal") == "strong" else I.t("pr_o_weak")
    return [{
        "type": "outlook", "title": title,
        "text": (I.t("pr_o_text", names=names, p=I.num(reg["production_t"]), lo=I.num(reg["low_t"]), hi=I.num(reg["high_t"]),
                     n=I.num(reg["normal_t"]), pct=f"{pct:+d}")
                 + (I.t("pr_o_drag", label=I.L(worst["label"]), e=f"{worst['effect_pct']:+.0f}") if worst else "")
                 + (I.t("pr_o_weakest", list=", ".join(low)) if low and len(low) < len(fc) else "") + " " + action
                 + sig),
        "numbers": {"region": reg},
        "assumptions": outlook["method"][-2:],
    }]
