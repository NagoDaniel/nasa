"""Shared helpers for the processing pipeline (raw downloads -> compact JSON).

Units = the 8 AOI counties (Alba + neighbours) and their communes, taken from the
app's own boundary layers so ids match the map: county `code` (e.g. "AB") and
commune `id` (e.g. "AB-0012").
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import box, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[2]  # backend/
DATA = ROOT / "data"
RAW = Path(os.environ.get("S2F_RAW_DIR", ROOT / ".cache" / "raw"))
AOI = ["AB", "AR", "BH", "CJ", "HD", "MS", "SB", "VL"]
YEARS = list(range(2015, 2026))


@dataclass(frozen=True)
class Unit:
    id: str
    kind: str  # "county" | "commune"
    name: str
    county: str
    geom: shapely.Geometry


@lru_cache(maxsize=1)
def load_units() -> tuple[Unit, ...]:
    counties = json.loads((DATA / "geo" / "counties.geojson.json").read_text())["features"]
    communes = json.loads((DATA / "geo" / "communes.geojson.json").read_text())["features"]
    out: list[Unit] = []
    for f in counties:
        p = f["properties"]
        if p["code"] in AOI:
            out.append(Unit(p["code"], "county", p["name"], p["code"], shape(f["geometry"])))
    for f in communes:
        p = f["properties"]
        if p["county"] in AOI:
            out.append(Unit(p["id"], "commune", p["name"], p["county"], shape(f["geometry"])))
    return tuple(out)


def raw(rel: str) -> Path:
    return RAW / rel


def first_existing(*rels: str) -> Path | None:
    """Full data lands in data/<sub-path>; samples in data/_samples/<sub-path>."""
    for r in rels:
        p = RAW / r
        if p.exists() and any(p.rglob("*")):
            return p
    return None


# --------------------------------------------------------------------------- grids
@dataclass
class GridWeights:
    """Per unit: flat cell indices into a (lat, lon) grid and normalised weights."""

    lat: np.ndarray
    lon: np.ndarray
    units: dict[str, tuple[np.ndarray, np.ndarray]]  # id -> (flat idx, weights)


def grid_weights(lat_centers, lon_centers, dlat: float, dlon: float) -> GridWeights:
    """Area-overlap weights of each grid cell with each unit (cos-lat corrected)."""
    lat = np.asarray(lat_centers, dtype=float)
    lon = np.asarray(lon_centers, dtype=float)
    cells, idx = [], []
    for i, la in enumerate(lat):
        for j, lo in enumerate(lon):
            cells.append(box(lo - dlon / 2, la - dlat / 2, lo + dlon / 2, la + dlat / 2))
            idx.append(i * len(lon) + j)
    tree = STRtree(cells)
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for u in load_units():
        hits = tree.query(u.geom, predicate="intersects")
        flat, w = [], []
        for h in hits:
            a = cells[h].intersection(u.geom).area
            if a > 0:
                la = lat[idx[h] // len(lon)]
                flat.append(idx[h])
                w.append(a * math.cos(math.radians(la)))
        if not flat:  # unit smaller than / outside grid: nearest cell
            c = u.geom.representative_point()
            i = int(np.abs(lat - c.y).argmin())
            j = int(np.abs(lon - c.x).argmin())
            flat, w = [i * len(lon) + j], [1.0]
        w_arr = np.asarray(w)
        out[u.id] = (np.asarray(flat), w_arr / w_arr.sum())
    return GridWeights(lat, lon, out)


def aggregate(values: np.ndarray, gw: GridWeights) -> dict[str, np.ndarray]:
    """values[..., lat, lon] -> {unit: values[...]} weighted mean, NaN-aware."""
    flat = values.reshape(values.shape[:-2] + (-1,))
    out = {}
    for uid, (cells, w) in gw.units.items():
        v = flat[..., cells]
        ok = ~np.isnan(v)
        ww = np.where(ok, w, 0.0)
        s = ww.sum(axis=-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[uid] = np.where(s > 0, np.nansum(np.where(ok, v, 0) * ww, axis=-1) / s, np.nan)
    return out


# --------------------------------------------------------------------------- output
def _clean(v, nd: int):
    if v is None:
        return None
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd)


def values(arr, nd: int = 2) -> list[float | None]:
    return [_clean(v, nd) for v in arr]


def write_json(rel: str, obj) -> Path:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  wrote data/{rel}  ({path.stat().st_size / 1e3:.0f} kB)")
    return path


def write_dataset(name: str, meta: dict, keys: list[str], units: dict[str, list]) -> Path:
    """Dataset in the compact schema documented in data/nasa/README.md:
    shared `keys` (periods) + one value array per unit, aligned with `keys`."""
    required = {"source", "variable", "unit", "period", "resolution", "confidence", "status", "label"}
    missing = required - meta.keys()
    if missing:
        raise ValueError(f"{name}: missing meta {missing}")
    for uid, arr in units.items():
        if len(arr) != len(keys):
            raise ValueError(f"{name}/{uid}: {len(arr)} values for {len(keys)} keys")
    return write_json(f"nasa/{name}.json", {**meta, "keys": keys, "units": units})


def month_keys(start_year: int, start_month: int, n: int) -> list[str]:
    out, y, m = [], start_year, start_month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out
