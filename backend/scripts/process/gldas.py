"""GLDAS Noah 2.1 monthly (0.25°) -> soil moisture, ET, rainfall per unit.

Two raw sources, same product:
  .cache/raw/land_model/gldas_noah025_monthly/GLDAS_NOAH025_M_<YYYYMM>_AOI.nc4  AOI clips (2015–2025)
  <repo>/data/gldas_monthly/GLDAS_NOAH025_M.A<YYYYMM>.021.nc4               global files (2021-11 – 2026-07)
Global files are cut to the AOI clip grid. Where both exist the AOI clip is used. Months
neither folder holds on this machine are carried over from the existing JSON
(common.merge_existing), so a partial raw folder never shrinks the processed series.
"""

from __future__ import annotations

import calendar
import re

import numpy as np
import xarray as xr

from common import aggregate, extra, grid_weights, merge_existing, raw, values, write_dataset

SOURCE = "NASA GLDAS Noah land surface model 2.1, monthly (GLDAS_NOAH025_M, GES DISC)"
CONF = {
    "county": "medium",
    "commune": "low",
    "note": "Model output (forced by observations), ~25 km cells; describes the area around a commune, not a single field.",
}
LV = 2.45e6  # J/kg latent heat of vaporisation
# AOI clip grid (cell centres), used for the global files too
LAT = (44.375, 47.625)
LON = (20.625, 25.375)


def _files() -> list[tuple[int, int, object, bool]]:
    """(year, month, path, is_global), one per month, AOI clip preferred."""
    by_month = {}
    for f in sorted(extra("gldas_monthly").glob("GLDAS_NOAH025_M.A*.021.nc4")):
        ym = re.search(r"\.A(\d{4})(\d{2})\.", f.name)
        by_month[(int(ym.group(1)), int(ym.group(2)))] = (f, True)
    for f in sorted(raw("land_model/gldas_noah025_monthly").glob("GLDAS_NOAH025_M_*_AOI.nc4")):
        ym = re.search(r"_(\d{4})(\d{2})_AOI", f.name)
        by_month[(int(ym.group(1)), int(ym.group(2)))] = (f, False)
    return [(y, m, f, g) for (y, m), (f, g) in sorted(by_month.items())]


def load():
    keys, out, lat, lon, bad = [], {}, None, None, []
    for y, m, f, is_global in _files():
        sec = 86400 * calendar.monthrange(y, m)[1]
        with xr.open_dataset(f) as ds:
            if is_global:
                ds = ds.sel(lat=slice(LAT[0] - 0.01, LAT[1] + 0.01), lon=slice(LON[0] - 0.01, LON[1] + 0.01))
            if "RootMoist_inst" not in ds:
                # Bad download (wrong product saved under this name): leave the month empty.
                print(f"  ! {f.name} does not contain GLDAS variables; {y}-{m:02d} left empty — re-download it")
                keys.append(f"{y:04d}-{m:02d}")
                bad.append(len(keys) - 1)
                continue
            ds = ds.isel(time=0).transpose("lat", "lon", ...)
            if lat is None:
                lat, lon = ds.lat.values.astype(float), ds.lon.values.astype(float)
            elif not (np.allclose(ds.lat.values, lat) and np.allclose(ds.lon.values, lon)):
                raise SystemExit(f"{f.name}: grid differs from the AOI clip grid")
            fields = {
                "rootmoist": ds.RootMoist_inst.values,
                "soilmoist_0_10": ds.SoilMoi0_10cm_inst.values,
                "et": ds.Evap_tavg.values * sec,  # kg/m²/s -> mm/month
                "rain": ds.Rainf_f_tavg.values * sec,
                "pet": ds.PotEvap_tavg.values * sec / LV,  # W/m² -> mm/month
            }
        keys.append(f"{y:04d}-{m:02d}")
        for k, v in fields.items():
            out.setdefault(k, []).append(np.asarray(v, dtype=float))
    # insert NaN grids for bad months so every key has a grid
    stacked = {}
    for k, grids in out.items():
        full = []
        it = iter(grids)
        for i in range(len(keys)):
            full.append(np.full_like(grids[0], np.nan) if i in bad else next(it))
        stacked[k] = np.stack(full)
    return keys, lat, lon, stacked, [keys[i] for i in bad]


def main() -> None:
    keys, lat, lon, f, missing = load()
    gw = grid_weights(lat, lon, 0.25, 0.25)
    base = {
        "source": SOURCE,
        "period": {"start": keys[0], "end": keys[-1], "step": "month"},
        "resolution": "0.25° grid (~25 km)",
        "confidence": CONF,
        "status": "complete",
        "missing_periods": missing,
    }
    defs = {
        "gldas_rootmoist": ("Root-zone soil moisture (0–100 cm)", "RootMoist_inst", "mm", "rootmoist", "mean", 1),
        "gldas_soilmoist_0_10": ("Topsoil moisture (0–10 cm)", "SoilMoi0_10cm_inst", "mm", "soilmoist_0_10", "mean", 1),
        "gldas_et": ("Evapotranspiration", "Evap_tavg", "mm", "et", "sum", 1),
        "gldas_pet": ("Potential evaporation", "PotEvap_tavg", "mm", "pet", "sum", 1),
        "gldas_rain": ("Rainfall (model forcing)", "Rainf_f_tavg", "mm", "rain", "sum", 1),
    }
    for name, (label, var, unit, key, how, nd) in defs.items():
        per_unit = aggregate(f[key], gw)
        k2, units, carried = merge_existing(name, keys, {u: values(v, nd) for u, v in per_unit.items()})
        if carried:
            print(f"  {name}: {len(carried)} months not in the raw folders here, kept from the previous build ({carried[0]} – {carried[-1]})")
        write_dataset(
            name,
            {**base, "label": label, "variable": var, "unit": unit, "aggregation": how,
             "period": {"start": k2[0], "end": k2[-1], "step": "month"},
             "missing_periods": [k for i, k in enumerate(k2) if all(v[i] is None for v in units.values())]},
            k2,
            units,
        )


if __name__ == "__main__":
    main()
