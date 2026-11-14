"""Hazard-year thresholds on the yearly agro indicators (stated assumptions).

A year counts as a hazard year for an indicator when it crosses the threshold.
Heat thresholds are physiological; rain / dry-spell / wet-day thresholds sit near
the regional 75th percentile of 2015–2025 (8 study counties), i.e. "an unusually
wet / dry year for this region". Shown to the user next to every score using them.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class Hazard:
    key: str
    op: str  # ">=" or "<="
    threshold: float
    text: str


HAZARDS: dict[str, Hazard] = {
    "heat35_jul_aug": Hazard("heat35_jul_aug", ">=", 3, "≥ 3 days at Tmax ≥ 35 °C in Jul–Aug"),
    "heat32_jul_aug": Hazard("heat32_jul_aug", ">=", 20, "≥ 20 days at Tmax ≥ 32 °C in Jul–Aug"),
    "rootmoist_jja_z": Hazard("rootmoist_jja_z", "<=", -1, "summer root-zone soil moisture ≥ 1 std below the 2015–2025 mean"),
    "dry_spell_apr_sep": Hazard("dry_spell_apr_sep", ">=", 15, "a dry spell of ≥ 15 days in Apr–Sep"),
    "rain_flowering_small_grain": Hazard("rain_flowering_small_grain", ">=", 200, "≥ 200 mm rain in 15 May–30 Jun"),
    "wet_days_flowering_small_grain": Hazard("wet_days_flowering_small_grain", ">=", 32, "≥ 32 wet days (≥ 1 mm) in 15 May–30 Jun"),
    "late_frost": Hazard("late_frost", ">=", 4, "≥ 4 frost days in 15 Apr–31 May"),
    "heat30_jun": Hazard("heat30_jun", ">=", 5, "≥ 5 days at Tmax ≥ 30 °C in June"),
    "rain_harvest_small_grain": Hazard("rain_harvest_small_grain", ">=", 100, "≥ 100 mm rain in July"),
    "rain_harvest_summer_crops": Hazard("rain_harvest_summer_crops", ">=", 150, "≥ 150 mm rain in Sep–Oct"),
}


def is_hazard(key: str, value: float | None) -> bool | None:
    if value is None:
        return None
    h = HAZARDS[key]
    return value >= h.threshold if h.op == ">=" else value <= h.threshold


def hazard_years(keys: list[str], agro_values: dict[str, list], years: list[int]) -> dict[int, list[str]]:
    """{year: [hazard keys hit]} for the given indicators."""
    out: dict[int, list[str]] = {}
    for i, y in enumerate(years):
        hit = []
        for k in keys:
            series = agro_values.get(k) or []
            v = series[i] if i < len(series) else None
            if is_hazard(k, v):
                hit.append(k)
        out[y] = hit
    return out


def crop_hazard_keys(trait: dict) -> list[str]:
    keys = list(trait["sensitive"]["hazards"])
    hh = trait["sensitive"].get("harvest_hazard")
    if hh and hh not in keys:
        keys.append(hh)
    return keys


def clean(xs) -> list[float]:
    return [float(x) for x in xs if x is not None and x > 0]


def median(xs) -> float | None:
    c = clean(xs)
    return statistics.median(c) if c else None


def cv(xs) -> float | None:
    c = clean(xs)
    if len(c) < 3:
        return None
    m = statistics.mean(c)
    return statistics.pstdev(c) / m if m else None


def percentile(xs, q: float) -> float | None:
    c = sorted(x for x in xs if x is not None)
    if not c:
        return None
    k = (len(c) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(c) - 1)
    return c[lo] + (c[hi] - c[lo]) * (k - lo)
