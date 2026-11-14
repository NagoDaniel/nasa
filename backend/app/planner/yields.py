"""Planning yields per crop and county, from the same model family as the season forecast.

For future seasons the weather is unknown, so the planning yield is the trend level with
average weather, and its range comes from the trend-only model's held-out errors (how far
real years fell from the trend). The trend is not extrapolated past the next season.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..scoring import forecast as F

_cache: dict[tuple, Any] = {}


def _data(crop: str, inputs: dict) -> tuple[str, dict]:
    proxy = F._proxy(crop, inputs["yields"])
    counties = list(inputs["counties"])
    return proxy, {
        "years": inputs["years"],
        "weather": inputs["counties"],
        "yields": {c: (inputs["yields"].get(c) or {}).get(proxy) for c in counties if (inputs["yields"].get(c) or {}).get(proxy)},
    }


def trend_model(crop: str, inputs: dict) -> dict | None:
    key = ("trend", crop, id(inputs))
    if key not in _cache:
        _, data = _data(crop, inputs)
        _cache[key] = F.evaluate([F.TREND], data) if data["yields"] else None
    return _cache[key]


def county_actual(crop: str, county: str, year: int, inputs: dict) -> float | None:
    proxy, data = _data(crop, inputs)
    ys = data["yields"].get(county)
    if not ys or year not in inputs["years"]:
        return None
    return ys[inputs["years"].index(year)]


def planning_yield(crop: str, county: str, inputs: dict, ins: dict, year: int) -> dict[str, Any] | None:
    """Normal yield (kg/ha) for `year` with 50 / 80 % ranges; falls back to INS 2015–2025 spread."""
    proxy, data = _data(crop, inputs)
    ys = data["yields"].get(county)
    ev = trend_model(crop, inputs)
    if ys and ev:
        med = float(np.median([v for v in ys if v]))
        mu, sd, a, b = ev["model"]
        last = max(y for y, v in zip(inputs["years"], ys) if v)
        y_eff = min(year, last + 1)  # no trend extrapolation beyond the next season
        anom = a + b[0] * (y_eff - mu[0]) / sd[0]
        normal = med * (1 + anom)
        q = ev["q"]
        return {"normal_kg_ha": normal, "range_kg_ha": {str(lv): [normal + med * q[lv][0], normal + med * q[lv][1]] for lv in (50, 80)},
                "basis": f"county trend {inputs['years'][0]}–{last}, ranges from held-out years", "confidence": "medium", "proxy": proxy if proxy != crop else None}
    # fallback: INS 2015–2025 (chickpea -> grain legumes, flax)
    key = crop if crop in (ins["counties"].get(county) or {}) and crop != "chickpea" else "grain_legumes"
    s = [v for v in ((ins["counties"].get(county, {}).get(key) or {}).get("yield_kg_ha") or []) if v]
    if len(s) < 5:
        return None
    med = float(np.median(s))
    return {"normal_kg_ha": med, "range_kg_ha": {"50": [float(np.percentile(s, 25)), float(np.percentile(s, 75))],
                                                  "80": [float(np.percentile(s, 10)), float(np.percentile(s, 90))]},
            "basis": f"INS county yields 2015–2025 ({'grain legumes as proxy' if key != crop else 'no long series'})",
            "confidence": "low", "proxy": key if key != crop else None}


def expected_county(crop: str, county: str, year: int, inputs: dict, ins: dict) -> float | None:
    """What the county got (INS) that year, else the trend normal — the yardstick for a field report."""
    a = county_actual(crop, county, year, inputs)
    if a:
        return a
    p = planning_yield(crop, county, inputs, ins, year)
    return p["normal_kg_ha"] if p else None
