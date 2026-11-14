"""NASA POWER daily grid (MERRA-2 0.5° x 0.625°) -> monthly indicators per unit."""

from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
import pandas as pd

from common import aggregate, grid_weights, raw, values, write_dataset

PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "GWETROOT", "EVPTRNS"]
SOURCE = "NASA POWER daily, community AG (power.larc.nasa.gov) — MERRA-2 / CERES"
RES = "0.5° × 0.625° grid (~50 km)"
CONF = {
    "county": "medium",
    "commune": "low",
    "note": "Regional grid: neighbouring communes share the same cells, so commune values describe the surrounding region, not the commune itself.",
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
    return dates, np.array(lats), np.array(lons), arrs


@lru_cache(maxsize=1)
def power_weights():
    _, lats, lons, _ = load_power_grid()
    return grid_weights(lats, lons, 0.5, 0.625)


def monthly(dates: pd.DatetimeIndex, arr: np.ndarray, how: str) -> tuple[list[str], np.ndarray]:
    keys = dates.strftime("%Y-%m")
    uniq = list(dict.fromkeys(keys))
    out = np.empty((len(uniq),) + arr.shape[1:])
    for k, key in enumerate(uniq):
        sel = arr[keys == key]
        out[k] = np.nansum(sel, axis=0) if how == "sum" else np.nanmean(sel, axis=0)
    return uniq, out


def main() -> None:
    dates, _, _, a = load_power_grid()
    gw = power_weights()
    period = {"start": dates[0].strftime("%Y-%m-%d"), "end": dates[-1].strftime("%Y-%m-%d"), "step": "month"}
    base = {"source": SOURCE, "period": period, "resolution": RES, "confidence": CONF, "status": "complete"}

    tmax = a["T2M_MAX"]
    defs = {
        "power_tmax": ("Mean daily maximum temperature", "T2M_MAX", "°C", tmax, "mean", 1),
        "power_tmean": ("Mean air temperature", "T2M", "°C", a["T2M"], "mean", 1),
        "power_heat_days": ("Hot days (Tmax ≥ 32 °C)", "T2M_MAX ≥ 32", "days", (tmax >= 32).astype(float), "sum", 1),
        "power_frost_days": ("Frost days (Tmin < 0 °C)", "T2M_MIN < 0", "days", (a["T2M_MIN"] < 0).astype(float), "sum", 1),
        "power_gdd10": ("Growing degree days (base 10 °C)", "max(T2M − 10, 0)", "°C·day", np.clip(a["T2M"] - 10, 0, None), "sum", 0),
        "power_precip": ("Precipitation (POWER, bias-corrected)", "PRECTOTCORR", "mm", a["PRECTOTCORR"], "sum", 1),
        "power_rh": ("Relative humidity", "RH2M", "%", a["RH2M"], "mean", 1),
        "power_soil_wetness": ("Root-zone soil wetness", "GWETROOT", "0–1", a["GWETROOT"], "mean", 3),
    }
    for name, (label, var, unit, arr, how, nd) in defs.items():
        keys, m = monthly(dates, arr, how)
        per_unit = aggregate(m, gw)
        write_dataset(
            name,
            {**base, "label": label, "variable": var, "unit": unit, "aggregation": how},
            keys,
            {uid: values(v, nd) for uid, v in per_unit.items()},
        )


if __name__ == "__main__":
    main()
