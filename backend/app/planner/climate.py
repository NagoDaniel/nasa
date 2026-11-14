"""Place-specific timing and weather odds for the field planner (pure functions).

Inputs: the county climatology in derived/forecast_inputs.json (NASA POWER 2000–2026):
frost dates, warm-up dates, 5-day (pentad) temperature and rain from 1 March, and the
yearly crop-window indicators. Everything is counted over past years: "8 in 10 years"
means 8 of the past seasons with data, not a weather forecast.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np

from ..scoring.hazards import HAZARDS, crop_hazard_keys, is_hazard
from ..scoring.forecast import RENAME

# the planner reads soil wetness from NASA POWER (2000–2026), not GLDAS, so the text differs
SOIL_Z_TEXT = "summer root-zone soil wetness ≥ 1 std below the 2000–2025 mean (NASA POWER)"


def _htext(k: str) -> str:
    return SOIL_Z_TEXT if k == "rootmoist_jja_z" else HAZARDS[k].text

PENTAD0 = 60  # day of year of 1 March (non-leap); pentads are 5-day steps from there
WET_HARVEST_MM = 40  # ≥ 40 mm in the 15 days after the expected harvest date = wet harvest
FROST_SAFE_SHARE = 0.9  # recommended maturity class must mature before the first autumn frost in ≥ 9 of 10 years


def doy_str(doy: float | None) -> str | None:
    if doy is None:
        return None
    d = date(2025, 1, 1) + timedelta(days=int(round(doy)) - 1)
    return f"{d.day} {d.strftime('%b')}"


def _pct(vals: list[float], q: float) -> float | None:
    v = [x for x in vals if x is not None]
    return float(np.percentile(v, q)) if v else None


def sowing(crop: str, trait: dict, clim: dict, years: list[int]) -> dict[str, Any]:
    """Sowing window: warm enough (7-day mean ≥ sow_temp_c) and, for frost-sensitive crops, after the last frost."""
    pl = trait["planner"]
    if pl["sow"] == "winter":
        return {"kind": "winter", "window": pl["sow_window"], "text": f"Sow in autumn, {pl['sow_window']} (the year before harvest)."}
    th = pl["sow_temp_c"]
    key = "warm10_doy" if th >= 10 else "warm8_doy" if th >= 8 else "warm5_doy"
    per_year = []
    for i, _ in enumerate(years):
        w = clim[key][i]
        f = clim["last_frost_doy"][i]
        if w is None or (pl["frost_sensitive"] and f is None):
            per_year.append(None)
            continue
        per_year.append(max(w, f + 1) if pl["frost_sensitive"] else w)
    ok = [d for d in per_year if d is not None]
    start, safe = _pct(ok, 50), _pct(ok, 80)
    late_frost = sum(1 for i, d in enumerate(per_year) if d is not None and clim["last_frost_doy"][i] is not None
                     and clim["last_frost_doy"][i] >= safe) if pl["frost_sensitive"] and safe else 0
    return {
        "kind": "spring", "per_year": per_year, "start_doy": start, "safe_doy": safe, "n_years": len(ok),
        "start": doy_str(start), "safe": doy_str(safe), "frost_after_safe": late_frost,
        "text": (f"Soil warm enough (7-day mean ≥ {th} °C){' and past the last frost' if pl['frost_sensitive'] else ''} "
                 f"by {doy_str(start)} in a typical year; by {doy_str(safe)} in 8 of 10 years."),
    }


def maturity(crop: str, trait: dict, clim: dict, years: list[int], sow: dict, cls: str) -> dict[str, Any] | None:
    """When a maturity class reaches maturity / harvest here, sown at each year's sowing date."""
    pl = trait["planner"]
    mc = (pl.get("maturity") or {}).get(cls)
    if not mc or sow["kind"] != "spring":
        return None
    need = mc["gdd10"]
    harvest, matured, before_frost, wet = [], 0, 0, 0
    n = 0
    for i, _ in enumerate(years):
        s = sow["per_year"][i]
        pt, pp = clim["pentad_t"][i], clim["pentad_p"][i]
        if s is None or not pt or pt[0] is None:
            continue
        n += 1
        k0 = max(0, int((s - PENTAD0) // 5))
        acc, m_doy = 0.0, None
        for k in range(k0, len(pt)):
            if pt[k] is None:
                break
            acc += 5 * max(pt[k] - 10, 0)
            if acc >= need:
                m_doy = PENTAD0 + 5 * k + 5
                break
        if m_doy is None:
            continue
        matured += 1
        ff = clim["first_frost_doy"][i]
        if ff is None or m_doy < ff:
            before_frost += 1
        h = m_doy + pl.get("harvest_after_maturity_days", 10)
        harvest.append(h)
        kh = int((h - PENTAD0) // 5)
        rain = [x for x in pp[kh: kh + 3] if x is not None]
        if len(rain) == 3 and sum(rain) >= WET_HARVEST_MM:
            wet += 1
    if n == 0:
        return None
    return {
        "class": cls, "label": mc["label"], "gdd10": need, "n_years": n,
        "matured_share": matured / n, "before_frost_share": before_frost / n,
        "harvest": doy_str(_pct(harvest, 50)), "harvest_late": doy_str(_pct(harvest, 80)),
        "harvest_doy": _pct(harvest, 50), "wet_harvest_share": wet / len(harvest) if harvest else None,
    }


def suggest_maturity(crop: str, trait: dict, clim: dict, years: list[int], sow: dict) -> tuple[str | None, list[dict]]:
    """Latest class that still matures before the first autumn frost in ≥ 9 of 10 years
    (longer maturity = more yield potential when the season allows it)."""
    opts = []
    for cls in ("early", "medium", "late"):
        m = maturity(crop, trait, clim, years, sow, cls)
        if m:
            opts.append(m)
    ok = [m for m in opts if m["before_frost_share"] >= FROST_SAFE_SHARE]
    return (ok[-1]["class"] if ok else (opts[0]["class"] if opts else None)), opts


def hazard_odds(crop: str, trait: dict, weather: dict, years: list[int], upto: int) -> dict[str, Any]:
    """How often the crop's sensitive window was hit here, per hazard and overall."""
    keys = crop_hazard_keys(trait)
    rows, any_hit, n = [], 0, 0
    idx = [i for i, y in enumerate(years) if y <= upto]
    for k in keys:
        series = weather.get(RENAME.get(k, k)) or []
        vals = [series[i] for i in idx if i < len(series) and series[i] is not None]
        if k == "rootmoist_jja_z":  # same threshold on the POWER soil-wetness z-score
            hits = sum(1 for v in vals if v <= HAZARDS[k].threshold)
        else:
            hits = sum(1 for v in vals if is_hazard(k, v))
        rows.append({"key": k, "text": _htext(k), "hits": hits, "years": len(vals)})
    for i in idx:
        vals = {k: ((weather.get(RENAME.get(k, k)) or [None] * len(years))[i]) for k in keys}
        if all(v is None for v in vals.values()):
            continue
        n += 1
        if any((v is not None and (v <= HAZARDS[k].threshold if k == "rootmoist_jja_z" else is_hazard(k, v))) for k, v in vals.items()):
            any_hit += 1
    return {"per_hazard": rows, "any_share": any_hit / n if n else None, "n_years": n,
            "window": trait["sensitive"]["window"], "stage": trait["sensitive"]["stage"]}


def water_odds(trait: dict, weather: dict, years: list[int], upto: int) -> dict[str, Any]:
    """Share of past seasons whose Apr–Sep rain covered the crop's water need (low / mid of its range)."""
    rain = [v for y, v in zip(years, weather.get("precip_apr_sep") or []) if v is not None and y <= upto]
    lo, hi = trait["water_need_mm"]
    mid = (lo + hi) / 2
    med = _pct(rain, 50)
    return {
        "need_mm": [lo, hi], "rain_median_mm": med, "n_years": len(rain),
        "typical_cover_pct": round(100 * med / mid) if med else None,
        "covers_low_share": sum(1 for r in rain if r >= lo) / len(rain) if rain else None,
        "covers_mid_share": sum(1 for r in rain if r >= mid) / len(rain) if rain else None,
        "note": "Growing-season rain only (Apr–Sep). The FAO water need is the crop's total use; the rest comes from water stored in the soil over winter (deep-rooted and winter crops use it most) or irrigation.",
    }


def season_check(crop: str, trait: dict, weather: dict, years: list[int], year: int) -> dict[str, Any] | None:
    """Weather-related quality (mycotoxin) risk of one past/current season for a crop grown in it."""
    if year not in years:
        return None
    i = years.index(year)
    hits = []
    for k in crop_hazard_keys(trait):
        v = (weather.get(RENAME.get(k, k)) or [None] * len(years))[i]
        if v is None:
            continue
        hit = v <= HAZARDS[k].threshold if k == "rootmoist_jja_z" else is_hazard(k, v)
        if hit:
            hits.append({"key": k, "text": _htext(k), "value": v})
    return {"year": year, "hits": hits, "level": "elevated" if hits else "normal",
            "quality": trait["sensitive"]["quality"]}
