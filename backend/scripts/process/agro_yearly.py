"""Yearly agro-climate indicators for crop-sensitive windows, per unit.

Computed per grid cell first, then area-weighted to units, so counts are
"expected days" for the unit. POWER (daily) gives the heat/frost/rain windows;
GLDAS (monthly) gives the water balance and soil-moisture anomaly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import gldas
from common import YEARS, aggregate, grid_weights, values, write_json
from power import load_power_grid, power_weights

POWER_SRC = "NASA POWER daily (MERRA-2)"
GLDAS_SRC = "NASA GLDAS Noah 2.1 monthly"

INDICATORS = {
    # key: (label, unit, source, window, why it matters)
    "heat35_jul_aug": ("Very hot days (Tmax ≥ 35 °C), Jul–Aug", "days", POWER_SRC, "Jul–Aug",
                       "Maize flowering/grain fill: heat + drought raise pollination failure and aflatoxin risk."),
    "heat32_jul_aug": ("Hot days (Tmax ≥ 32 °C), Jul–Aug", "days", POWER_SRC, "Jul–Aug",
                       "Heat stress for summer crops (maize, sunflower) during flowering and grain fill."),
    "heat30_jun": ("Hot days (Tmax ≥ 30 °C), June", "days", POWER_SRC, "Jun",
                   "Heat at flowering of spring pulses, oats and flax (pea pod set drops above ~30 °C)."),
    "tmax_jul_aug": ("Mean Tmax, Jul–Aug", "°C", POWER_SRC, "Jul–Aug", "Overall summer heat load."),
    "late_frost": ("Late frost days (Tmin < 0 °C), 15 Apr–31 May", "days", POWER_SRC, "15 Apr–31 May",
                   "Frost after spring sowing damages emerging spring crops (sunflower, maize, chickpea, flax)."),
    "rain_flowering_small_grain": ("Rain, 15 May–30 Jun", "mm", POWER_SRC, "15 May–30 Jun",
                                   "Wet weather at small-grain flowering (wheat, barley, oats) raises Fusarium / mycotoxin risk."),
    "wet_days_flowering_small_grain": ("Wet days (≥ 1 mm), 15 May–30 Jun", "days", POWER_SRC, "15 May–30 Jun",
                                       "Frequent rain days during flowering favour Fusarium infection."),
    "rh_flowering_small_grain": ("Mean relative humidity, 15 May–30 Jun", "%", POWER_SRC, "15 May–30 Jun",
                                 "High humidity during flowering favours Fusarium infection."),
    "rain_harvest_small_grain": ("Rain in July (small-grain harvest)", "mm", POWER_SRC, "Jul",
                                 "Rain at harvest causes sprouting, quality loss and harvest delays."),
    "rain_harvest_summer_crops": ("Rain, Sep–Oct (maize/sunflower harvest)", "mm", POWER_SRC, "Sep–Oct",
                                  "Wet harvests raise drying costs and mould / mycotoxin risk."),
    "precip_apr_sep": ("Growing-season precipitation, Apr–Sep", "mm", POWER_SRC, "Apr–Sep",
                       "Water available to spring/summer crops."),
    "dry_spell_apr_sep": ("Longest dry spell (< 1 mm/day), Apr–Sep", "days", POWER_SRC, "Apr–Sep",
                          "Long dry spells cause drought stress, worst when they hit flowering."),
    "gdd10_apr_sep": ("Growing degree days (base 10 °C), Apr–Sep", "°C·day", POWER_SRC, "Apr–Sep",
                      "Heat units available for warm-season crops like maize and sunflower."),
    "et_apr_sep": ("Evapotranspiration, Apr–Sep", "mm", GLDAS_SRC, "Apr–Sep", "Water used by vegetation and soil."),
    "water_balance_apr_sep": ("Water balance (rain − ET), Apr–Sep", "mm", GLDAS_SRC, "Apr–Sep",
                              "Negative = vegetation used more water than fell as rain (drawing down soil water)."),
    "rootmoist_jja": ("Root-zone soil moisture, Jun–Aug mean", "mm", GLDAS_SRC, "Jun–Aug",
                      "Water in the root zone during the critical summer months."),
    "rootmoist_jja_z": ("Root-zone soil moisture anomaly, Jun–Aug", "z-score", GLDAS_SRC, "Jun–Aug",
                        "Compared with 2015–2025: below −1 = clearly drier summer than usual."),
}


def _window(dates: pd.DatetimeIndex, y: int, start: tuple[int, int], end: tuple[int, int]) -> np.ndarray:
    s = pd.Timestamp(y, *start)
    e = pd.Timestamp(y, *end)
    return (dates >= s) & (dates <= e)


def _longest_run(dry: np.ndarray) -> np.ndarray:
    """dry[day, ...] bool -> longest consecutive True run per cell."""
    run = np.zeros(dry.shape[1:])
    best = np.zeros(dry.shape[1:])
    for d in dry:
        run = np.where(d, run + 1, 0)
        best = np.maximum(best, run)
    return best


def power_part() -> dict[str, np.ndarray]:
    dates, _, _, a = load_power_grid()
    tmax, tmin, pr, rh, t = a["T2M_MAX"], a["T2M_MIN"], a["PRECTOTCORR"], a["RH2M"], a["T2M"]
    shape = (len(YEARS),) + tmax.shape[1:]
    out = {k: np.full(shape, np.nan) for k in INDICATORS if INDICATORS[k][2] == POWER_SRC}
    for i, y in enumerate(YEARS):
        ja = _window(dates, y, (7, 1), (8, 31))
        fl = _window(dates, y, (5, 15), (6, 30))
        fr = _window(dates, y, (4, 15), (5, 31))
        jul = _window(dates, y, (7, 1), (7, 31))
        so = _window(dates, y, (9, 1), (10, 31))
        gs = _window(dates, y, (4, 1), (9, 30))
        if not gs.any():
            continue
        out["heat35_jul_aug"][i] = (tmax[ja] >= 35).sum(0)
        out["heat32_jul_aug"][i] = (tmax[ja] >= 32).sum(0)
        out["tmax_jul_aug"][i] = np.nanmean(tmax[ja], 0)
        out["heat30_jun"][i] = (tmax[_window(dates, y, (6, 1), (6, 30))] >= 30).sum(0)
        out["late_frost"][i] = (tmin[fr] < 0).sum(0)
        out["rain_flowering_small_grain"][i] = np.nansum(pr[fl], 0)
        out["wet_days_flowering_small_grain"][i] = (pr[fl] >= 1).sum(0)
        out["rh_flowering_small_grain"][i] = np.nanmean(rh[fl], 0)
        out["rain_harvest_small_grain"][i] = np.nansum(pr[jul], 0)
        out["rain_harvest_summer_crops"][i] = np.nansum(pr[so], 0)
        out["precip_apr_sep"][i] = np.nansum(pr[gs], 0)
        out["dry_spell_apr_sep"][i] = _longest_run(pr[gs] < 1)
        out["gdd10_apr_sep"][i] = np.nansum(np.clip(t[gs] - 10, 0, None), 0)
    gw = power_weights()
    return {k: aggregate(v, gw) for k, v in out.items()}


def gldas_part() -> dict[str, dict[str, np.ndarray]]:
    keys, lat, lon, f, _ = gldas.load()
    months = np.array([int(k[5:7]) for k in keys])
    years = np.array([int(k[:4]) for k in keys])
    shape = (len(YEARS),) + f["et"].shape[1:]
    et, wb, rm = (np.full(shape, np.nan) for _ in range(3))
    for i, y in enumerate(YEARS):
        gs = (years == y) & (months >= 4) & (months <= 9)
        jja = (years == y) & (months >= 6) & (months <= 8)
        if gs.sum() == 6:
            et[i] = f["et"][gs].sum(0)
            wb[i] = f["rain"][gs].sum(0) - f["et"][gs].sum(0)
        if jja.sum() == 3:
            rm[i] = f["rootmoist"][jja].mean(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (rm - np.nanmean(rm, 0)) / np.nanstd(rm, 0)
    gw = grid_weights(lat, lon, 0.25, 0.25)
    return {
        "et_apr_sep": aggregate(et, gw),
        "water_balance_apr_sep": aggregate(wb, gw),
        "rootmoist_jja": aggregate(rm, gw),
        "rootmoist_jja_z": aggregate(z, gw),
    }


def main() -> None:
    parts = {**power_part(), **gldas_part()}
    unit_ids = next(iter(parts.values())).keys()
    units = {u: {k: values(parts[k][u], 1 if k != "rootmoist_jja_z" else 2) for k in INDICATORS} for u in unit_ids}
    write_json(
        "derived/agro_yearly.json",
        {
            "years": YEARS,
            "indicators": {
                k: {"label": l, "unit": un, "source": s, "window": w, "why": why}
                for k, (l, un, s, w, why) in INDICATORS.items()
            },
            "confidence": {
                "county": "medium",
                "commune": "low",
                "note": "From regional grids (POWER ~50 km, GLDAS ~25 km). Day counts are area-weighted averages, so they can be fractional.",
            },
            "units": units,
        },
    )


if __name__ == "__main__":
    main()
