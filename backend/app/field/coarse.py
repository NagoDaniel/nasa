"""Surrounding-area estimates for a drawn field from coarse datasets.

A field gets the value of each native grid cell it touches (POWER ~50 km, GPM IMERG
~11 km, GLDAS ~25 km), together with the cell outline and how much of the cell the field
covers. Values are never interpolated or downscaled: a smaller selection does not make
these numbers more precise. Soil comes from SoilGrids 250 m pixels; SMAP only exists as
commune averages in this project.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Geod
from shapely.geometry import Polygon, box, mapping

from ..config import BASE_DIR
from ..json_store import store
from ..i18n import L, t

GEOD = Geod(ellps="WGS84")

CELL_DATASETS = {
    # name: (what it tells the farmer, how to read it)
    "imerg_precip": "Rain measured from satellites (calibrated with gauges).",
    "power_precip": "Rain from the POWER reanalysis model (coarser; also covers months IMERG lacks).",
    "power_tmax": "Average daily maximum air temperature.",
    "power_heat_days": "Days with maximum temperature ≥ 32 °C.",
    "gldas_rootmoist": "Water in the top 1 m of soil, from the GLDAS land model.",
}

SOIL_DIR = BASE_DIR / ".cache" / "raw" / "soil" / "soilgrids"
SOIL_PROPS = {  # prop: (label, divisor, unit)
    "phh2o": ("pH (water)", 10, "pH"),
    "soc": ("Soil organic carbon", 10, "g/kg"),
    "clay": ("Clay", 10, "%"),
    "sand": ("Sand", 10, "%"),
    "silt": ("Silt", 10, "%"),
    "nitrogen": ("Total nitrogen", 100, "g/kg"),
}
SOIL_DEPTHS = [("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)]


def _km2(geom) -> float:
    return abs(GEOD.geometry_area_perimeter(geom)[0]) / 1e6


def _yearly(keys: list[str], vals: list, how: str) -> dict[str, float]:
    by: dict[str, list] = {}
    for k, v in zip(keys, vals):
        by.setdefault(k[:4], []).append(v)
    out = {}
    for y, vs in by.items():
        if len(vs) == 12 and all(v is not None for v in vs):
            out[y] = round(sum(vs) if how == "sum" else sum(vs) / 12, 1)
    return out


def cell_context(name: str, field: Polygon) -> dict[str, Any] | None:
    try:
        d = store.get(f"cells/{name}.json")
    except FileNotFoundError:
        return None
    lat, lon, dlat, dlon = d["lat"], d["lon"], d["dlat"], d["dlon"]
    field_km2 = _km2(field)
    cells = []
    minx, miny, maxx, maxy = field.bounds
    for i, la in enumerate(lat):
        if la + dlat / 2 < miny or la - dlat / 2 > maxy:
            continue
        for j, lo in enumerate(lon):
            if lo + dlon / 2 < minx or lo - dlon / 2 > maxx:
                continue
            cell = box(lo - dlon / 2, la - dlat / 2, lo + dlon / 2, la + dlat / 2)
            inter = cell.intersection(field)
            if inter.is_empty or inter.area <= 0:
                continue
            vals = d["cells"].get(f"{i},{j}")
            ckm2 = _km2(cell)
            entry: dict[str, Any] = {
                "cell": f"{i},{j}", "center": [lo, la], "geometry": mapping(cell),
                "cell_area_km2": round(ckm2, 1),
                "share_of_field_pct": round(100 * inter.area / field.area, 1),
                "field_share_of_cell_pct": round(100 * field_km2 / ckm2, 4) if ckm2 else None,
            }
            if vals is None:
                entry["status"] = "no_data"
            else:
                last = next((k for k, v in zip(reversed(d["keys"]), reversed(vals)) if v is not None), None)
                entry.update(
                    status="ok",
                    yearly=_yearly(d["keys"], vals, d["aggregation"]),
                    latest_month={"month": last, "value": vals[d["keys"].index(last)]} if last else None,
                    last_12_months=[{"month": k, "value": v} for k, v in list(zip(d["keys"], vals))[-12:]],
                    missing_months=sum(1 for v in vals if v is None),
                )
            cells.append(entry)
    if not cells:
        return None
    return {
        "dataset": name, "label": d["label"], "unit": d["unit"], "aggregation": d["aggregation"],
        "about": CELL_DATASETS.get(name, ""), "source": d["source"], "resolution": d["resolution"],
        "period": {"start": d["keys"][0], "end": d["keys"][-1]}, "last_day": d.get("last_day"),
        "kind": "surrounding_area_estimate",
        "note": t("fd_cell_note", res=L(d["resolution"])),
        "cells": cells,
    }


def soil_context(field: Polygon) -> dict[str, Any]:
    """SoilGrids 250 m pixels under the field (model prediction, mean of the pixel)."""
    base = {"source": "ISRIC SoilGrids 2.0 (CC BY 4.0), predicted mean, 0–30 cm depth-weighted",
            "kind": "model_pixels", "properties": {k: {"label": v[0], "unit": v[2]} for k, v in SOIL_PROPS.items()}}
    if not SOIL_DIR.exists():
        return {**base, "status": "unavailable", "note": "SoilGrids rasters are not on this server; see the commune soil values."}
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.windows import Window, from_bounds

    out: dict[str, Any] = {}
    pixel_info = None
    for prop, (_, div, _) in SOIL_PROPS.items():
        acc = None
        for depth, w in SOIL_DEPTHS:
            p = SOIL_DIR / f"{prop}_{depth}_mean.tif"
            if not p.exists():
                return {**base, "status": "unavailable", "note": f"Missing {p.name}"}
            with rasterio.open(p) as src:
                w0 = from_bounds(*field.bounds, src.transform)
                c0, r0 = math.floor(w0.col_off), math.floor(w0.row_off)
                win = Window(c0, r0, math.ceil(w0.col_off + w0.width) - c0 + 1, math.ceil(w0.row_off + w0.height) - r0 + 1)
                a = src.read(1, window=win, boundless=True, fill_value=0).astype(float)
                tr = src.window_transform(win)
                res = src.res
            a[a == 0] = np.nan
            acc = a * w if acc is None else acc + a * w
        vals = acc / 30 / div
        inside = geometry_mask([mapping(field)], out_shape=vals.shape, transform=tr, invert=True)
        how = "pixel centres inside the field"
        if not inside.any():
            inside = geometry_mask([mapping(field)], out_shape=vals.shape, transform=tr, invert=True, all_touched=True)
            how = "pixels touching the field (the field is smaller than one pixel)"
        sel = vals[inside & ~np.isnan(vals)]
        out[prop] = None if sel.size == 0 else {
            "mean": round(float(sel.mean()), 2), "min": round(float(sel.min()), 2), "max": round(float(sel.max()), 2)}
        if pixel_info is None:
            rows, cols = np.nonzero(inside)
            px = [box(*(tr * (c, r + 1)), *(tr * (c + 1, r))) for r, c in zip(rows, cols)]
            lat0 = field.centroid.y
            w_m = res[0] * 111_320 * math.cos(math.radians(lat0))
            h_m = res[1] * 110_574
            pixel_info = {"count": int(inside.sum()), "selection": how,
                          "pixel_size_m": [round(w_m), round(h_m)], "pixel_area_ha": round(w_m * h_m / 10_000, 2),
                          "pixels": {"type": "FeatureCollection",
                                     "features": [{"type": "Feature", "properties": {}, "geometry": mapping(g)} for g in px[:400]]}}
    if all(v is None for v in out.values()):
        return {**base, "status": "no_data", "resolution": "250 m", "pixels": pixel_info, "values": out,
                "note": "SoilGrids has no prediction for these pixels (usually built-up land or water)."}
    return {**base, "status": "ok", "resolution": "250 m (resampled to ~0.0023° in this project)", "pixels": pixel_info,
            "values": out,
            "note": "A prediction from a global soil model, not a measurement of your field. Fields smaller than one pixel "
                    "get that pixel's value. Take soil samples for decisions on liming or fertiliser."}


def smap_context(commune_id: str | None) -> dict[str, Any] | None:
    """SMAP surface soil moisture exists only as commune averages (9 km cells) in this project."""
    if not commune_id:
        return None
    try:
        d = store.get("nasa/smap_soil_moisture.json")
    except FileNotFoundError:
        return None
    vals = d["units"].get(commune_id)
    if not vals:
        return {"dataset": "smap_soil_moisture", "status": "no_data", "source": d["source"], "resolution": d["resolution"],
                "note": "SMAP was only processed for communes around Alba Iulia; none for this commune."}
    last = next((k for k, v in zip(reversed(d["keys"]), reversed(vals)) if v is not None), None)
    return {"dataset": "smap_soil_moisture", "status": "ok", "label": d["label"], "unit": d["unit"], "source": d["source"],
            "resolution": d["resolution"], "kind": "commune_average", "commune": commune_id,
            "latest_month": {"month": last, "value": vals[d["keys"].index(last)]} if last else None,
            "last_12_months": [{"month": k, "value": v} for k, v in list(zip(d["keys"], vals))[-12:]],
            "note": "Average over the commune of 9 km SMAP cells (surface ~5 cm). It cannot show differences between fields."}


def context(field: Polygon, commune_id: str | None) -> dict[str, Any]:
    return {
        "cells": [c for n in CELL_DATASETS if (c := cell_context(n, field))],
        "soil": soil_context(field),
        "smap": smap_context(commune_id),
    }


def soil_dir_exists() -> bool:
    return Path(SOIL_DIR).exists()
