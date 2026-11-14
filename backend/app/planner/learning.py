"""Learning from what farmers report (harvest reports + past yields entered in the planner).

1. Field level: how this field yields compared with its county that year (INS county yield,
   or the trend normal when INS has no figure yet). Averaged on a log scale and pulled toward
   0 until the field has several seasons: factor = exp(n / (n + FIELD_PRIOR) · mean log ratio).
2. Shared rotation effects, pooled over all fields: the yield bonus of a cereal after a grain
   legume, and the penalty of repeating a crop. Measured on what is left after each field's
   level, then blended with the literature value: (n·measured + PRIOR·literature) / (n + PRIOR),
   so a handful of reports moves the value only a little.
Pure functions: reports are plain dicts {field_id, year, crop, yield_t_ha, county}.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Callable

FIELD_PRIOR = 3  # seasons
EFFECT_PRIOR = 10  # reports


def _ratios(reports: list[dict], expected: Callable[[str, str, int], float | None]) -> list[tuple[dict, float]]:
    out = []
    for r in reports:
        if not r.get("yield_t_ha"):
            continue
        e = expected(r["crop"], r["county"], r["year"])
        if e:
            out.append((r, math.log(r["yield_t_ha"] * 1000 / e)))
    return out


def field_level(reports: list[dict], expected: Callable[[str, str, int], float | None]) -> dict[str, Any]:
    lr = _ratios(reports, expected)
    n = len(lr)
    if n == 0:
        return {"factor": 1.0, "n": 0, "raw_pct": None, "pct": 0.0, "weight": 0.0, "seasons": []}
    m = sum(x for _, x in lr) / n
    w = n / (n + FIELD_PRIOR)
    return {
        "factor": math.exp(w * m), "n": n, "raw_pct": round(100 * (math.exp(m) - 1), 1), "pct": round(100 * (math.exp(w * m) - 1), 1),
        "weight": round(w, 2),
        "seasons": [{"year": r["year"], "crop": r["crop"], "yield_t_ha": r["yield_t_ha"], "vs_county_pct": round(100 * (math.exp(x) - 1))}
                    for r, x in sorted(lr, key=lambda t: t[0]["year"])],
    }


def shared_effects(all_reports: list[dict], expected: Callable[[str, str, int], float | None], traits: dict) -> dict[str, Any]:
    by_field: dict[int, list[dict]] = defaultdict(list)
    for r in all_reports:
        by_field[r["field_id"]].append(r)
    after_leg, after_other, repeat, no_repeat = [], [], [], []
    for fid, reps in by_field.items():
        lr = _ratios(reps, expected)
        if not lr:
            continue
        level = sum(x for _, x in lr) / len(lr)
        crop_by_year = {r["year"]: r["crop"] for r in reps}
        for r, x in lr:
            prev = crop_by_year.get(r["year"] - 1)
            if prev is None:
                continue
            resid = x - level
            if traits["crops"].get(r["crop"], {}).get("family") == "cereal":
                (after_leg if traits["crops"].get(prev, {}).get("legume") else after_other).append(resid)
            (repeat if prev == r["crop"] else no_repeat).append(resid)
    A = traits["assumptions"]

    def blend(lit: float, a: list[float], b: list[float], sign: int) -> dict[str, Any]:
        n = min(len(a), len(b))
        obs = sign * (math.exp(sum(a) / len(a) - sum(b) / len(b)) - 1) if a and b else None
        used = lit if obs is None else (n * obs + EFFECT_PRIOR * lit) / (n + EFFECT_PRIOR)
        return {"literature": lit, "measured": None if obs is None else round(obs, 3), "n": n, "used": round(used, 3),
                "groups": [len(a), len(b)]}

    return {
        "legume_precrop_yield_bonus": blend(A["legume_precrop_yield_bonus"]["value"], after_leg, after_other, +1),
        "repeat_penalty": blend(A["repeat_penalty"]["value"], repeat, no_repeat, -1),
        "n_reports": len(all_reports), "n_fields": len(by_field),
        "prior": {"field_seasons": FIELD_PRIOR, "effect_reports": EFFECT_PRIOR},
    }


def problems_summary(reports: list[dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for r in reports:
        for p in r.get("problems") or []:
            out[p] += 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
