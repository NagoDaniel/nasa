"""GRACE / GRACE-FO JPL mascon (RL06.3 v04, CRI filtered) -> monthly water-storage anomaly per unit.

Raw: <repo>/data/grace_tws/GRCTellus.JPL.*.GLO.RL06.3M.MSCNv04CRI.nc (one global file,
0.5° grid, 2002-04 onward). `lwe_thickness` = liquid-water-equivalent anomaly in cm
relative to the 2004–2009 mean. The 0.5° grid is a sampling of ~3° mascons, so the
real resolution is ~300 km: every unit sees the regional signal. JPL's optional CLM
gain factors (`scale_factor`) are not applied (they are model-based and make the
region patchy at 0.5°).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd
import xarray as xr

from common import aggregate, extra, grid_weights, month_keys, values, write_dataset


def main() -> None:
    files = sorted(extra("grace_tws").glob("GRCTellus.JPL.*.nc"))
    if not files:
        print("  no GRACE file, skipping")
        return
    with xr.open_dataset(files[-1]) as ds:
        sub = ds.sel(lat=slice(44.0, 48.0), lon=slice(20.0, 26.0))
        lat, lon = sub.lat.values.astype(float), sub.lon.values.astype(float)
        lwe = sub.lwe_thickness.transpose("time", "lat", "lon").values.astype(float)
        unc = sub.uncertainty.transpose("time", "lat", "lon").values.astype(float)
        tb = sub.time_bounds.values.astype("datetime64[ns]").astype("int64")
        mid = pd.DatetimeIndex(tb.mean(axis=1).astype("int64").astype("datetime64[ns]"))
    # A month can hold two solutions (2012-01, 2015-04): average them
    by = defaultdict(list)
    for i, t in enumerate(mid):
        by[t.strftime("%Y-%m")].append(i)
    first, last = min(by), max(by)
    n = (int(last[:4]) - int(first[:4])) * 12 + int(last[5:]) - int(first[5:]) + 1
    keys = month_keys(int(first[:4]), int(first[5:]), n)
    grid = np.full((len(keys),) + lwe.shape[1:], np.nan)
    ugrid = np.full_like(grid, np.nan)
    for i, k in enumerate(keys):
        if k in by:
            grid[i] = lwe[by[k]].mean(axis=0)
            ugrid[i] = unc[by[k]].mean(axis=0)
    gw = grid_weights(lat, lon, 0.5, 0.5)
    per_unit = aggregate(grid, gw)
    u_ab = aggregate(ugrid, gw)["AB"]
    empty = [k for i, k in enumerate(keys) if np.isnan(per_unit["AB"][i])]
    med_unc = float(np.nanmedian(u_ab))
    print(f"  {len(keys)} months {keys[0]} – {keys[-1]}, {len(empty)} without a solution; median 1σ uncertainty (Alba) {med_unc:.1f} cm")
    write_dataset(
        "grace_tws",
        {
            "label": "Total water storage anomaly (groundwater + soil + surface)",
            "source": "NASA/DLR GRACE & GRACE-FO, JPL mascon RL06.3 v04 CRI (TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4, PO.DAAC)",
            "variable": "lwe_thickness",
            "unit": "cm",
            "aggregation": "mean",
            "period": {"start": keys[0], "end": keys[-1], "step": "month"},
            "resolution": "~300 km (3° mascons on a 0.5° grid)",
            "confidence": {
                "county": "low",
                "commune": "low",
                "note": "Satellite gravimetry: all water stored in a ~300 km region (groundwater, soil, rivers, snow) as cm of water vs the 2004–2009 mean. "
                "Shows the regional long-term trend, not a commune or field value. "
                f"Typical 1σ uncertainty ≈ {med_unc:.1f} cm. Gaps: GRACE ended mid-2017, GRACE-FO started mid-2018, and some single months are missing.",
            },
            "status": "complete",
            "missing_periods": empty,
        },
        keys,
        {u: values(v, 1) for u, v in per_unit.items()},
    )


if __name__ == "__main__":
    main()
