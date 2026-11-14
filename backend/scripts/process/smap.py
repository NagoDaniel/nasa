"""SMAP L3 enhanced daily soil moisture (SPL3SMP_E, 9 km EASE-Grid 2.0) -> monthly per unit.

Raw: <repo>/data/smap/<YYYY-MM>_<n>_SMAP_L3_SM_P_E_<YYYYMMDD>_..._subsetted.nc4, a
Harmony subset of ~45.6–46.5 °N, 23.0–24.2 °E (14 × 9 cells around Alba Iulia).
So only units that this box covers ≥ MIN_COVER get a series (≈ 100 communes + Alba county).

Per cell and day: mean of the AM (6 am) and PM (6 pm) retrievals whose
retrieval_qual_flag bit 0 is 0 ("recommended quality"; frozen / snow-covered /
dense-vegetation retrievals are flagged and dropped). Per cell and month: mean of
valid days, kept when ≥ MIN_DAYS. Then area-weighted to units.
"""

from __future__ import annotations

import re
from collections import defaultdict

import netCDF4
import numpy as np
from pyproj import Transformer
from shapely.geometry import box

from common import aggregate, cell_weights, extra, GridWeights, month_keys, values, write_dataset

MIN_COVER = 0.85
MIN_DAYS = 5
MIN_VALID = 0.5
HALF = 9008.055210146 / 2  # EASE-Grid 2.0 global 9 km cell size, m


def _read(f) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with netCDF4.Dataset(f) as n:
        x = n.variables["x_global"][:].data
        y = n.variables["y_global"][:].data
        vals = []
        for grp, sfx in (("Soil_Moisture_Retrieval_Data_AM", ""), ("Soil_Moisture_Retrieval_Data_PM", "_pm")):
            g = n.groups[grp]
            sm = np.ma.filled(g.variables[f"soil_moisture{sfx}"][:].astype(float), np.nan)
            q = np.ma.filled(g.variables[f"retrieval_qual_flag{sfx}"][:], 1)
            sm[(q & 1) != 0] = np.nan
            sm[(sm < 0.02) | (sm > 0.6)] = np.nan
            vals.append(sm)
    with np.errstate(invalid="ignore"):
        day = np.nanmean(np.stack(vals), axis=0)
    return x, y, day


def main() -> None:
    files = {}
    for f in sorted(extra("smap").glob("*_SMAP_L3_SM_P_E_*_subsetted.nc4")):
        if f.name.startswith("test_"):
            continue  # leftover from a test run (see dataset_dani.md)
        d = re.search(r"_SM_P_E_(\d{8})_", f.name).group(1)
        files[d] = f  # dedupe by date: month chunks overlap by a day
    if not files:
        print("  no SMAP files, skipping")
        return
    x = y = None
    by_month: dict[str, list[np.ndarray]] = defaultdict(list)
    for d, f in sorted(files.items()):
        xx, yy, day = _read(f)
        if x is None:
            x, y = xx, yy
        elif not (np.allclose(xx, x) and np.allclose(yy, y)):
            raise SystemExit(f"{f.name}: subset grid differs")
        by_month[f"{d[:4]}-{d[4:6]}"].append(day)

    first, last = min(by_month), max(by_month)
    n = (int(last[:4]) - int(first[:4])) * 12 + int(last[5:]) - int(first[5:]) + 1
    keys = month_keys(int(first[:4]), int(first[5:]), n)
    grid = np.full((len(keys), len(y), len(x)), np.nan)
    for i, k in enumerate(keys):
        days = by_month.get(k)
        if not days:
            continue
        st = np.stack(days)
        cnt = (~np.isnan(st)).sum(axis=0)
        with np.errstate(invalid="ignore"):
            grid[i] = np.where(cnt >= MIN_DAYS, np.nanmean(st, axis=0), np.nan)

    # EASE-Grid 2.0 (EPSG:6933) cell -> lon/lat box (cylindrical equal-area: edges stay straight)
    tr = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)
    cells, idx = [], []
    for i, yc in enumerate(y):
        for j, xc in enumerate(x):
            lo0, la0 = tr.transform(xc - HALF, yc - HALF)
            lo1, la1 = tr.transform(xc + HALF, yc + HALF)
            cells.append(box(lo0, la0, lo1, la1))
            idx.append(i * len(x) + j)
    gw = GridWeights(np.asarray(y), np.asarray(x), cell_weights(cells, idx, min_cover=MIN_COVER))
    per_unit = aggregate(grid, gw, min_valid=MIN_VALID)
    # units whose cells never pass the quality flag (forested mountains) get no series
    units = {u: values(v, 3) for u, v in per_unit.items() if np.isfinite(v).any()}
    n_days = len(files)
    empty = [k for i, k in enumerate(keys) if all(v[i] is None for v in units.values())]
    print(f"  {n_days} daily files {min(files)} – {max(files)}, {len(units)} units; months without data: {len(empty)}")
    write_dataset(
        "smap_soil_moisture",
        {
            "label": "Surface soil moisture (satellite, 0–5 cm)",
            "source": "NASA SMAP L3 Enhanced radiometer daily soil moisture SPL3SMP_E v006 (NSIDC DAAC, Harmony subset)",
            "variable": "soil_moisture (AM + PM)",
            "unit": "m³/m³",
            "aggregation": "mean",
            "period": {"start": keys[0], "end": keys[-1], "step": "month"},
            "resolution": "9 km EASE-Grid 2.0",
            "confidence": {
                "county": "medium",
                "commune": "low",
                "note": "Only the area around Alba Iulia was downloaded (≈ 45.6–46.5 °N, 23.0–24.2 °E), so only Alba county and nearby communes have values. "
                "One 9 km cell covers many fields, and SMAP sees only the top ~5 cm. Recommended-quality retrievals only: frozen or snow-covered "
                "ground in winter and forested mountain cells are dropped, so winter months are often empty. No SMAP data 2022-08-07 – 2022-09-19 (source gap).",
            },
            "status": "complete",
            "missing_periods": empty,
        },
        keys,
        units,
    )


if __name__ == "__main__":
    main()
