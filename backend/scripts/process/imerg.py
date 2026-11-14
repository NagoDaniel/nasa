"""GPM IMERG Final V07 monthly (0.1°) -> monthly precipitation per unit."""

from __future__ import annotations

import calendar
import re

import netCDF4
import numpy as np
import xarray as xr

from common import aggregate, grid_weights, raw, values, write_dataset


def from_daily(y: int, m: int):
    days = sorted(raw(f"precipitation/gpm_imerg_daily/{y}").glob(f"IMERG_daily_{y}{m:02d}*_AOI.nc4"))
    n = calendar.monthrange(y, m)[1]
    if len(days) != n:
        raise SystemExit(f"IMERG daily {y}-{m:02d}: {len(days)}/{n} files, cannot rebuild month")
    total, lat, lon = None, None, None
    for f in days:
        with xr.open_dataset(f) as ds:
            p = ds.precipitation.isel(time=0).transpose("lat", "lon")  # mm/day
            v = np.where(p.values < 0, np.nan, p.values.astype(float))
            lat, lon = p.lat.values.astype(float), p.lon.values.astype(float)
        total = v if total is None else total + v
    return total, lat, lon


def main() -> None:
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
                mm = p.values.astype(float) * 24 * calendar.monthrange(y, m)[1]  # mm/hr -> mm/month
        else:
            # Bad download (a daily file saved under the monthly name): rebuild from daily files.
            mm, la, lo = from_daily(y, m)
            print(f"  ! {f.name} is not a monthly file; rebuilt {y}-{m:02d} from daily IMERG")
            if lat is None:
                lat, lon = la, lo
        keys.append(f"{y:04d}-{m:02d}")
        grids.append(np.where(mm < 0, np.nan, mm))
    gw = grid_weights(lat, lon, 0.1, 0.1)
    per_unit = aggregate(np.stack(grids), gw)
    write_dataset(
        "imerg_precip",
        {
            "label": "Precipitation (satellite)",
            "source": "NASA GPM IMERG Final Run V07B, monthly (GES DISC)",
            "variable": "precipitation",
            "unit": "mm",
            "aggregation": "sum",
            "period": {"start": keys[0], "end": keys[-1], "step": "month"},
            "resolution": "0.1° grid (~11 km)",
            "confidence": {
                "county": "high",
                "commune": "medium",
                "note": "Satellite + gauge-calibrated. The Final archive ends 2025-09; Oct–Dec 2025 are not available yet (POWER precipitation covers them).",
            },
            "status": "complete",
        },
        keys,
        {u: values(v, 1) for u, v in per_unit.items()},
    )


if __name__ == "__main__":
    main()
