"""Season yield outlook per county (the project's AI component: forecasting).

Model, per crop, pooled over the 8 study counties, trained on 2000–2025:

    anomaly = yield / county median yield − 1
    anomaly ≈ a + Σ b_j · z_j        (ridge regression, z_j = standardised predictor)

Predictors: the crop's own sensitive-window weather indicators from crop_traits.json
(e.g. maize: very hot days in Jul–Aug, summer soil wetness, dry spell, harvest rain),
plus a linear year trend (varieties and farming change over 26 years).
Inputs: derived/forecast_inputs.json (NASA POWER per county, INS yields from 2000).

Honesty rules:
- Tested leave-one-year-out: every year is predicted by a model fitted without it
  (medians and scaling included). All errors and intervals come from these tests.
- Benchmark = "normal year" = the trend alone (same leave-one-year-out test). Skill is
  what the weather adds on top; if it is < MIN_SKILL the forecast is marked unreliable.
- "Normal" for the forecast season = trend level with average weather, so the verdict
  and the drivers show the weather effect only.
- Intervals = percentiles of the held-out errors: the 80 % interval contained 8 in 10
  of the past held-out years.
Pure functions: all inputs are passed in.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .hazards import crop_hazard_keys

LAMBDA = 2.0  # ridge penalty on standardised predictors
MIN_SKILL = 0.1  # weather signal "strong": cuts the benchmark's mean error by ≥ 10 %
WEAK_SKILL = 0.05  # "weak" between 5 and 10 %; below that "none" (range = usual swing around the trend)
MIN_ROWS = 40
TREND = "trend"
# agro_yearly keys -> forecast_inputs keys (GLDAS soil moisture -> POWER soil wetness)
RENAME = {"rootmoist_jja_z": "gwetroot_jja_z"}
# when an indicator does not exist yet for the forecast season, use an earlier-window stand-in
STAND_IN = {"gwetroot_jja_z": "gwetroot_jj_z"}
LEVELS = (50, 80, 90)


def _proxy(crop: str, yields: dict) -> str:
    return "grain_legumes" if crop == "chickpea" or not any(crop in v for v in yields.values()) else crop


def _fit(X: np.ndarray, y: np.ndarray):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    a = y.mean()
    b = np.linalg.solve(Z.T @ Z + LAMBDA * np.eye(Z.shape[1]), Z.T @ (y - a))
    return mu, sd, a, b


def _predict(model, X: np.ndarray) -> np.ndarray:
    mu, sd, a, b = model
    return a + ((X - mu) / sd) @ b


def _x(keys, vals: dict, years: list[int], year: int) -> list[float] | None:
    i = years.index(year)
    x = [float(year) if k == TREND else (vals.get(k) or [None] * len(years))[i] for k in keys]
    return None if any(v is None for v in x) else [float(v) for v in x]


def _rows(keys, data, exclude_year=None):
    """(county, year, x, yield, median) rows; medians use years other than exclude_year only."""
    years = data["years"]
    out = []
    for c, ys in data["yields"].items():
        train_vals = [v for y, v in zip(years, ys) if v and y != exclude_year]
        if len(train_vals) < 8:
            continue
        med = float(np.median(train_vals))
        for i, y in enumerate(years):
            v = ys[i]
            x = _x(keys, data["weather"].get(c, {}), years, y)
            if v and x is not None:
                out.append((c, y, x, v, med))
    return out


def evaluate(keys: list[str], data: dict) -> dict[str, Any] | None:
    """Leave-one-year-out test of the model on these predictors."""
    rows = _rows(keys, data)
    if len(rows) < MIN_ROWS:
        return None
    err_m, err_b, held = [], [], {}
    for y in sorted({r[1] for r in rows}):
        fold = _rows(keys, data, exclude_year=y)
        train = [r for r in fold if r[1] != y]
        test = [r for r in fold if r[1] == y]
        if not test or len(train) < MIN_ROWS:
            continue
        Xtr, ytr = np.array([r[2] for r in train]), np.array([r[3] / r[4] - 1 for r in train])
        Xte = np.array([r[2] for r in test])
        m = _fit(Xtr, ytr)
        pred = _predict(m, Xte)
        if TREND in keys:  # benchmark: trend only
            j = keys.index(TREND)
            base = _predict(_fit(Xtr[:, [j]], ytr), Xte[:, [j]])
        else:
            base = np.full(len(test), ytr.mean())
        for r, p, pb in zip(test, pred, base):
            actual = r[3] / r[4] - 1
            err_m.append(actual - p)
            err_b.append(actual - pb)
            held[(r[0], y)] = (float(p), float(actual), r[4])
    if len(err_m) < MIN_ROWS:
        return None
    e_m, e_b = np.array(err_m), np.array(err_b)
    mae_m, mae_b = float(np.abs(e_m).mean()), float(np.abs(e_b).mean())
    full = _fit(np.array([r[2] for r in rows]), np.array([r[3] / r[4] - 1 for r in rows]))
    q = {lv: (float(np.percentile(e_m, 50 - lv / 2)), float(np.percentile(e_m, 50 + lv / 2))) for lv in LEVELS}
    return {
        "model": full, "n": len(rows), "years": sorted({r[1] for r in rows}),
        "mae": mae_m, "mae_base": mae_b, "skill": 1 - mae_m / mae_b if mae_b else 0.0, "q": q, "held": held,
    }


def _label(k: str, meta: dict) -> tuple[str, str]:
    if k == TREND:
        return "Long-term trend", "year"
    return meta[k]["label"], meta[k]["unit"]


def forecast(crop: str, counties: dict[str, str], ins: dict, inputs: dict, traits: dict) -> dict[str, Any]:
    t = traits["crops"][crop]
    meta = inputs["indicators"]
    years = inputs["years"]
    proxy = _proxy(crop, inputs["yields"])
    data = {
        "years": years,
        "weather": {c: inputs["counties"].get(c, {}) for c in counties},
        "yields": {c: (inputs["yields"].get(c) or {}).get(proxy) for c in counties if (inputs["yields"].get(c) or {}).get(proxy)},
    }
    weather_keys = [RENAME.get(k, k) for k in crop_hazard_keys(t)]
    all_keys = tuple(weather_keys + [TREND])
    ins_years = ins["years"]
    cache: dict[tuple, dict | None] = {}

    def model_for(keys: tuple) -> dict | None:
        if keys not in cache:
            cache[keys] = evaluate(list(keys), data) if keys else None
        return cache[keys]

    def model_info(keys: tuple, ev: dict) -> dict:
        mu, sd, a, b = ev["model"]
        return {
            "predictors": [{"key": k, "label": _label(k, meta)[0], "unit": _label(k, meta)[1],
                            "effect_pct_per_unit": round(100 * b[j] / sd[j], 2)} for j, k in enumerate(keys)],
            "n_county_years": ev["n"], "years": [ev["years"][0], ev["years"][-1]],
            "mae_pct": round(100 * ev["mae"], 1), "mae_normal_year_pct": round(100 * ev["mae_base"], 1),
            "skill_pct": round(100 * ev["skill"]), "reliable": ev["skill"] >= MIN_SKILL,
            "signal": "strong" if ev["skill"] >= MIN_SKILL else "weak" if ev["skill"] >= WEAK_SKILL else "none",
            "intervals_pct": {str(lv): [round(100 * lo, 1), round(100 * hi, 1)] for lv, (lo, hi) in ev["q"].items()},
        }

    full = model_for(all_keys)
    last_yield_year = max((y for c in data["yields"] for y, v in zip(years, data["yields"][c]) if v), default=None)
    out: dict[str, Any] = {}
    for c in counties:
        rec: dict[str, Any] = {"forecast": None, "history": []}
        ys = data["yields"].get(c)
        w = data["weather"].get(c, {})
        if not ys:
            out[c] = rec
            continue
        med = float(np.median([v for v in ys if v]))
        has = lambda k, i: k == TREND or (w.get(k) or [None] * len(years))[i] is not None  # noqa: E731
        fy = next((y for y in reversed(years) if last_yield_year and y > last_yield_year
                   and all(has(k, years.index(y)) or (k in STAND_IN and has(STAND_IN[k], years.index(y))) for k in all_keys)), None)
        if fy is not None:
            i = years.index(fy)
            keys = tuple(k if has(k, i) else STAND_IN[k] for k in all_keys)
            ev = model_for(keys)
            if ev:
                x = np.array([_x(keys, w, years, fy)])
                mu, sd, a, b = ev["model"]
                anom = float(_predict(ev["model"], x)[0])
                z = (x[0] - mu) / sd
                # normal = trend level for this season with average weather (weather z = 0)
                norm = a + sum(b[j] * z[j] for j, k in enumerate(keys) if k == TREND)
                normal_kg = med * (1 + norm)
                band = {str(lv): [round(med * (1 + anom + lo)), round(med * (1 + anom + hi))] for lv, (lo, hi) in ev["q"].items()}
                area_s = ((ins["counties"].get(c, {}).get(proxy)) or {}).get("area_ha") or []
                prod_s = ((ins["counties"].get(c, {}).get(proxy)) or {}).get("production_t") or []
                area = next((v for v in reversed(area_s) if v), None)
                latest_prod = next(((y, v) for y, v in zip(reversed(ins_years), reversed(prod_s)) if v), None)
                rec["forecast"] = {
                    "year": fy, "median_kg_ha": round(normal_kg), "long_median_kg_ha": round(med),
                    "yield_kg_ha": round(med * (1 + anom)),
                    "intervals_kg_ha": band, "low_kg_ha": band["80"][0], "high_kg_ha": band["80"][1],
                    "anomaly_pct": round(100 * (anom - norm) / (1 + norm), 1),
                    # weather effects, in % of the normal (trend) yield
                    "contributions": [{"key": k, "label": _label(k, meta)[0], "unit": _label(k, meta)[1],
                                       "value": round(float(x[0][j]), 1), "effect_pct": round(100 * b[j] * z[j] / (1 + norm), 1)}
                                      for j, k in enumerate(keys) if k != TREND],
                    "model": model_info(keys, ev),
                    # idea 5: supply outlook = latest area × yield range
                    "supply": None if not area else {
                        "area_ha": area, "area_year": max(y for y, v in zip(ins_years, area_s) if v),
                        "production_t": round(area * med * (1 + anom) / 1000),
                        "intervals_t": {k: [round(area * v[0] / 1000), round(area * v[1] / 1000)] for k, v in band.items()},
                        "low_t": round(area * band["80"][0] / 1000), "high_t": round(area * band["80"][1] / 1000),
                        "normal_t": round(area * normal_kg / 1000), "vs_normal_pct": round(100 * (anom - norm) / (1 + norm)),
                        "latest_t": round(latest_prod[1]) if latest_prod else None,
                        "latest_year": latest_prod[0] if latest_prod else None,
                    },
                }
        # back-test history for the chart: actual vs held-out prediction with its 80 % band
        if full:
            lo80, hi80 = full["q"][80]
            for y, v in zip(years, ys):
                h = full["held"].get((c, y))
                rec["history"].append({
                    "year": y, "actual_kg_ha": round(v) if v else None,
                    "predicted_kg_ha": round(h[2] * (1 + h[0])) if h else None,
                    "low_kg_ha": round(h[2] * (1 + h[0] + lo80)) if h else None,
                    "high_kg_ha": round(h[2] * (1 + h[0] + hi80)) if h else None,
                })
        out[c] = rec

    fc = [r["forecast"] for r in out.values() if r["forecast"] and r["forecast"]["supply"] and r["forecast"]["model"]["signal"] != "none"]
    region = None
    if fc:
        region = {
            "year": max(f["year"] for f in fc), "counties": [c for c, r in out.items() if r["forecast"] in fc],
            "production_t": sum(f["supply"]["production_t"] for f in fc),
            "low_t": sum(f["supply"]["low_t"] for f in fc), "high_t": sum(f["supply"]["high_t"] for f in fc),
            "normal_t": sum(f["supply"]["normal_t"] for f in fc),
            "signal": "strong" if all(f["model"]["signal"] == "strong" for f in fc) else "weak",
            "latest_t": sum(f["supply"]["latest_t"] or 0 for f in fc),
        }
    held = list(full["held"].values()) if full else []
    inside = sum(1 for p, a, _ in held if full["q"][80][0] <= a - p <= full["q"][80][1]) if full else 0
    return {
        "crop": crop, "proxy": proxy if proxy != crop else None,
        "model": model_info(all_keys, full) if full else None,
        "coverage_80_pct": round(100 * inside / len(held)) if held else None,
        "counties": out, "region": region,
        "method": [
            "Yield anomaly (yield ÷ county median − 1) = ridge regression on the crop's sensitive-window weather indicators "
            f"plus a year trend, pooled over the 8 counties, 2000–2025 (penalty λ = {LAMBDA} on standardised predictors).",
            "Tested leave-one-year-out: each year is predicted by a model that never saw it. Errors and intervals come from these tests.",
            f"Benchmark: a normal year = the long-term trend alone. Weather signal: strong if adding the weather cuts the benchmark error by ≥ {MIN_SKILL:.0%}, "
            f"weak at {WEAK_SKILL:.0%}–{MIN_SKILL:.0%}, none below (then the range is just the usual swing around the trend).",
            "More indicators were tested (summer Tmax, Apr–Sep rain, GDD, early soil wetness): they made held-out errors worse, so each crop keeps only its own sensitive-window indicators.",
            "Normal for the forecast season = the trend level with average weather; the verdict and drivers show the weather effect only.",
            "Intervals = percentiles of the held-out errors: the 80 % interval held 8 in 10 past years, the 50 % interval 1 in 2.",
            "Supply = latest INS area × yield; assumes the area planted does not change. Normal = same area × normal (trend) yield.",
        ],
        "limits": [
            "County level: INS publishes yields per county only; a field can differ a lot.",
            "26 seasons: extremes worse than anything since 2000 are not learned; intervals assume the future errs like the past.",
            "Weather and a straight-line trend only: prices, fertiliser, pests and area changes are not in the model; a county whose yields stopped rising (e.g. Alba maize since 2018) may get a normal that is too high.",
            "Weather is NASA POWER at ~50 km; associations, not proof of cause.",
            "The latest season can still change: POWER's last weeks are provisional and late crops may not be harvested yet.",
        ],
        "sources": [
            "INS TEMPO AGR110A (county yield 2000–2025), AGR108A / AGR109A (area, production)",
            "NASA POWER daily, 2000–2026 (derived/forecast_inputs.json)",
            "Crop sensitive windows: crop_traits.json",
        ],
    }
