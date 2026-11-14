"""Native grid cells of the coarse datasets -> data/cells/<name>.json.

Used for drawn fields: a field gets the value of the grid cell(s) it lies in, together
with the cell outline, so the app can show that the value describes the whole cell
(the surrounding area) and not the field. No interpolation, no downscaling.

Schema: {label, unit, aggregation, source, resolution, dlat, dlon, lat: [cell centre],
lon: [cell centre], keys: ["YYYY-MM", ...], cells: {"<i>,<j>": [value per key]}}
Only cells with at least one value are written.
"""

from __future__ import annotations

import calendar
import re

import netCDF4
import numpy as np
import xarray as xr

import gldas
import power
from common import raw, values, write_json


def _write(name: str, meta: dict, keys: list[str], lat, lon, dlat: float, dlon: float, grid: np.ndarray, nd: int) -> None:
    cells = {}
    for i in range(len(lat)):
        for j in range(len(lon)):
            v = grid[:, i, j]
            if not np.all(np.isnan(v)):
                cells[f"{i},{j}"] = values(v, nd)
    write_json(f"cells/{name}.json", {
        **meta, "dlat": dlat, "dlon": dlon,
        "lat": [round(float(x), 4) for x in lat], "lon": [round(float(x), 4) for x in lon],
        "keys": keys, "cells": cells,
    })


def _power() -> None:
    dates, lat, lon, a = power.load_power_grid()
    keep = dates >= power.pd.Timestamp(power.SERIES_START)  # same period as the unit series (loader now holds 2000–2026)
    dates, a = dates[keep], {k: v[keep] for k, v in a.items()}
    base = {"source": power.SOURCE, "resolution": power.RES, "last_day": dates[-1].strftime("%Y-%m-%d")}
    tmax = a["T2M_MAX"]
    defs = {
        "power_tmax": ("Mean daily maximum temperature", "°C", tmax, "mean", 1),
        "power_heat_days": ("Hot days (Tmax ≥ 32 °C)", "days", power.flag(tmax >= 32, tmax), "sum", 1),
        "power_precip": ("Precipitation (POWER, bias-corrected)", "mm", a["PRECTOTCORR"], "sum", 1),
    }
    for name, (label, unit, arr, how, nd) in defs.items():
        keys, m = power.monthly(dates, arr, how)
        _write(name, {**base, "label": label, "unit": unit, "aggregation": how}, keys, lat, lon, 0.5, 0.625, m, nd)


def _imerg() -> None:
    files = sorted(raw("precipitation/gpm_imerg_monthly").glob("IMERG_monthly_*_AOI.nc4"))
    keys, grids, lat, lon = [], [], None, None
    for f in files:
        ym = re.search(r"_(\d{4})(\d{2})_", f.name)
        y, m = int(ym.group(1)), int(ym.group(2))
        with netCDF4.Dataset(f) as nc:
            has_grid = "Grid" in nc.groups
        if has_grid:
            with xr.open_dataset(f, group="Grid") as ds:
                p = ds.precipitation.isel(time=0).transpose("lat", "lon")
                if lat is None:
                    lat, lon = p.lat.values.astype(float), p.lon.values.astype(float)
                mm = p.values.astype(float) * 24 * calendar.monthrange(y, m)[1]
        else:
            from imerg import from_daily
            mm, la, lo = from_daily(y, m)
            if lat is None:
                lat, lon = la, lo
        keys.append(f"{y:04d}-{m:02d}")
        grids.append(np.where(mm < 0, np.nan, mm))
    _write("imerg_precip", {"label": "Precipitation (satellite)", "unit": "mm", "aggregation": "sum",
                            "source": "NASA GPM IMERG Final Run V07B, monthly (GES DISC)", "resolution": "0.1° grid (~11 km)"},
           keys, lat, lon, 0.1, 0.1, np.stack(grids), 1)


def _gldas() -> None:
    keys, lat, lon, f, _ = gldas.load()
    _write("gldas_rootmoist", {"label": "Root-zone soil moisture (0–100 cm)", "unit": "mm", "aggregation": "mean",
                               "source": gldas.SOURCE, "resolution": "0.25° grid (~25 km)"},
           keys, lat, lon, 0.25, 0.25, f["rootmoist"], 1)


def main() -> None:
    _power()
    _imerg()
    _gldas()


if __name__ == "__main__":
    main()
