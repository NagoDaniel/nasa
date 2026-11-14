"""NASA POWER daily grid (MERRA-2 0.5° x 0.625°) -> monthly indicators per unit.

Two raw sources:
  .cache/raw/nasa_power/daily_grid/*.csv  56 native cells over the study area, 2015–2025
  <repo>/data/power/power_<lat>_<lon>.json 9 points around Alba Iulia, 2021-11 – 2026-10
Each point returns the value of the native cell containing it (checked: identical to the
CSV of that cell over 2021-11 – 2025-12), so the points only add days after the CSV end
to those 9 cells. Other cells stay empty for those days, and units are only given a value
when cells with data carry ≥ MIN_VALID of their area.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from common import aggregate, extra, grid_weights, raw, values, write_dataset

MIN_VALID = 0.75

PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "GWETROOT", "EVPTRNS"]
SOURCE = "NASA POWER daily, community AG (power.larc.nasa.gov) — MERRA-2 / CERES"
RES = "0.5° × 0.625° grid (~50 km)"
CONF = {
    "county": "medium",
    "commune": "low",
    "note": "Regional grid: neighbouring communes share the same cells, so commune values describe the surrounding region, not the commune itself. "
    "2026 (Jan–Oct) only exists for the 9 cells around Alba Iulia (roughly Alba, Sibiu and parts of the neighbouring counties).",
}


@lru_cache(maxsize=1)
def load_power_grid():
    files = sorted(raw("nasa_power/daily_grid").glob("power_daily_*.csv"))
    if not files:
        raise SystemExit("POWER files not found")
    pts = []
    for f in files:
        m = re.match(r"power_daily_(-?[\d.]+)_(-?[\d.]+)\.csv", f.name)
        pts.append((float(m.group(1)), float(m.group(2)), f))
    lats = sorted({p[0] for p in pts})
    lons = sorted({p[1] for p in pts})
    dates = None
    arrs = {p: None for p in PARAMS}
    for la, lo, f in pts:
        lines = f.read_text().splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith("YEAR,DOY"))
        df = pd.read_csv(f, skiprows=start)
        df = df.replace(-999, np.nan)
        d = pd.to_datetime(df["YEAR"].astype(str) + df["DOY"].astype(str).str.zfill(3), format="%Y%j")
        if dates is None:
            dates = pd.DatetimeIndex(d)
            for p in PARAMS:
                arrs[p] = np.full((len(d), len(lats), len(lons)), np.nan)
        i, j = lats.index(la), lons.index(lo)
        for p in PARAMS:
            arrs[p][:, i, j] = df[p].to_numpy(dtype=float)
    return _extend_with_points(dates, np.array(lats), np.array(lons), arrs)


def _extend_with_points(dates, lats, lons, arrs):
    """Append days after the grid end from the point files, on the cell holding each point."""
    files = sorted(extra("power").glob("power_*.json"))
    if not files:
        return dates, lats, lons, arrs
    series = []
    for f in files:
        d = json.loads(f.read_text())
        lo, la = d["geometry"]["coordinates"][:2]
        i, j = int(np.abs(lats - la).argmin()), int(np.abs(lons - lo).argmin())
        par = d["properties"]["parameter"]
        df = pd.DataFrame({p: par[p] for p in PARAMS if p in par})
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df = df.replace(-999, np.nan)
        series.append((i, j, df))
    last = max(df.index.max() for _, _, df in series)
    if last <= dates[-1]:
        return dates, lats, lons, arrs
    new_dates = pd.date_range(dates[0], last, freq="D")
    n_old = len(dates)
    out = {}
    for p, a in arrs.items():
        b = np.full((len(new_dates),) + a.shape[1:], np.nan)
        b[:n_old] = a
        out[p] = b
    for i, j, df in series:
        tail = df[df.index > dates[-1]].reindex(new_dates[n_old:])
        for p in PARAMS:
            if p in tail:
                out[p][n_old:, i, j] = tail[p].to_numpy(dtype=float)
    print(f"  POWER points: {len(series)} cells extended {new_dates[n_old].date()} – {last.date()}")
    return pd.DatetimeIndex(new_dates), lats, lons, out


@lru_cache(maxsize=1)
def power_weights():
    _, lats, lons, _ = load_power_grid()
    return grid_weights(lats, lons, 0.5, 0.625)


def monthly(dates: pd.DatetimeIndex, arr: np.ndarray, how: str) -> tuple[list[str], np.ndarray]:
    """Daily -> monthly per cell; a cell-month with < 90% valid days is left empty."""
    keys = dates.strftime("%Y-%m")
    uniq = list(dict.fromkeys(keys))
    out = np.empty((len(uniq),) + arr.shape[1:])
    for k, key in enumerate(uniq):
        sel = arr[keys == key]
        ok = (~np.isnan(sel)).sum(axis=0) >= 0.9 * len(sel)
        with np.errstate(invalid="ignore"):
            v = np.nansum(sel, axis=0) if how == "sum" else np.nanmean(sel, axis=0)
        out[k] = np.where(ok, v, np.nan)
    return uniq, out


def flag(cond: np.ndarray, src: np.ndarray) -> np.ndarray:
    """Boolean condition as 0/1, NaN where the source value is missing."""
    return np.where(np.isnan(src), np.nan, cond.astype(float))


def main() -> None:
    dates, _, _, a = load_power_grid()
    gw = power_weights()
    period = {"start": dates[0].strftime("%Y-%m-%d"), "end": dates[-1].strftime("%Y-%m-%d"), "step": "month"}
    base = {"source": SOURCE, "period": period, "resolution": RES, "confidence": CONF, "status": "complete"}

    tmax = a["T2M_MAX"]
    defs = {
        "power_tmax": ("Mean daily maximum temperature", "T2M_MAX", "°C", tmax, "mean", 1),
        "power_tmean": ("Mean air temperature", "T2M", "°C", a["T2M"], "mean", 1),
        "power_heat_days": ("Hot days (Tmax ≥ 32 °C)", "T2M_MAX ≥ 32", "days", flag(tmax >= 32, tmax), "sum", 1),
        "power_frost_days": ("Frost days (Tmin < 0 °C)", "T2M_MIN < 0", "days", flag(a["T2M_MIN"] < 0, a["T2M_MIN"]), "sum", 1),
        "power_gdd10": ("Growing degree days (base 10 °C)", "max(T2M − 10, 0)", "°C·day", np.clip(a["T2M"] - 10, 0, None), "sum", 0),
        "power_precip": ("Precipitation (POWER, bias-corrected)", "PRECTOTCORR", "mm", a["PRECTOTCORR"], "sum", 1),
        "power_rh": ("Relative humidity", "RH2M", "%", a["RH2M"], "mean", 1),
        "power_soil_wetness": ("Root-zone soil wetness", "GWETROOT", "0–1", a["GWETROOT"], "mean", 3),
    }
    for name, (label, var, unit, arr, how, nd) in defs.items():
        keys, m = monthly(dates, arr, how)
        per_unit = aggregate(m, gw, min_valid=MIN_VALID)
        write_dataset(
            name,
            {**base, "label": label, "variable": var, "unit": unit, "aggregation": how},
            keys,
            {uid: values(v, nd) for uid, v in per_unit.items()},
        )


if __name__ == "__main__":
    main()
