"""MODIS MOD13Q1 NDVI (250 m, 16-day) -> mean NDVI per unit and composite.

Reads the full AppEEARS output from data/<sub-path> when present, else the Alba
2024 sample in data/_samples/<sub-path> (marked status "sample").
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import numpy as np
import rasterio

from common import first_existing, values, write_dataset
from zonal import label_raster, unit_pixel_groups

SUB = "vegetation/modis_mod13q1_ndvi_evi"


def doy_to_date(s: str) -> str:
    y, d = int(s[:4]), int(s[4:7])
    return (date(y, 1, 1) + timedelta(days=d - 1)).isoformat()


def main() -> None:
    full = first_existing(SUB)
    root = full or first_existing(f"_samples/{SUB}")
    if root is None:
        print("  no MOD13Q1 data yet, skipping")
        return
    status = "complete" if full else "sample"
    ndvi_files = sorted(root.rglob("*_250m_16_days_NDVI_doy*.tif"))
    keys, per_unit = [], {}
    groups = None
    for f in ndvi_files:
        doy = re.search(r"_doy(\d{7})", f.name).group(1)
        rel_f = next(root.rglob(f"*pixel_reliability_doy{doy}*.tif"), None)
        with rasterio.open(f) as src:
            a = src.read(1).astype(float)
            if groups is None:
                groups = unit_pixel_groups(*label_raster(src.transform, src.shape))
        a[(a <= -2000) | (a > 10000)] = np.nan
        if rel_f is not None:
            with rasterio.open(rel_f) as r:
                rel = r.read(1)
            a[(rel < 0) | (rel > 1)] = np.nan  # keep good (0) and marginal (1)
        a *= 0.0001
        keys.append(doy_to_date(doy))
        flat = a.ravel()
        for uid, idx in groups.items():
            if idx.size == 0:
                continue
            v = flat[idx]
            ok = v[~np.isnan(v)]
            # require ≥ 30% clear pixels, otherwise the composite is too cloudy for this unit
            per_unit.setdefault(uid, []).append(float(ok.mean()) if ok.size >= 0.3 * idx.size else np.nan)
    order = np.argsort(keys)
    keys = [keys[i] for i in order]
    units = {u: values(np.array(v)[order], 3) for u, v in per_unit.items() if np.isfinite(v).any()}
    print(f"  {len(keys)} composites, {keys[0]} – {keys[-1]}, {len(units)} units with data ({status})")
    write_dataset(
        "modis_ndvi",
        {
            "label": "Vegetation index (NDVI)",
            "source": "NASA MODIS Terra MOD13Q1.061 via AppEEARS",
            "variable": "NDVI",
            "unit": "NDVI",
            "aggregation": "mean",
            "period": {"start": keys[0], "end": keys[-1], "step": "16-day"},
            "resolution": "250 m",
            "confidence": {
                "county": "high" if status == "complete" else "medium",
                "commune": "medium",
                "note": ("Sample: Alba county, one year only — the full 2015–2025 set is still processing. " if status == "sample" else "")
                + "Mean over all land cover (not yet cropland-only); good/marginal-quality pixels, composites with < 30% clear pixels dropped.",
            },
            "status": status,
        },
        keys,
        units,
    )


if __name__ == "__main__":
    main()
