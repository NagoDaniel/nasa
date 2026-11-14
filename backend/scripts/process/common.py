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
# Second raw folder: <repo>/data (gitignored; documented in dataset_dani.md). Alba-Iulia box
# downloads for 2021-11 – 2026-10 plus whole-tile / global files (MODIS h19v04, GLDAS, GRACE).
RAW_EXTRA = Path(os.environ.get("S2F_RAW_EXTRA_DIR", ROOT.parent / "data"))
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


def extra(rel: str) -> Path:
    return RAW_EXTRA / rel


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


def grid_weights(lat_centers, lon_centers, dlat: float, dlon: float, min_cover: float = 0.0) -> GridWeights:
    """Area-overlap weights of each cell of a regular lat/lon grid with each unit (cos-lat corrected)."""
    lat = np.asarray(lat_centers, dtype=float)
    lon = np.asarray(lon_centers, dtype=float)
    cells, idx = [], []
    for i, la in enumerate(lat):
        for j, lo in enumerate(lon):
            cells.append(box(lo - dlon / 2, la - dlat / 2, lo + dlon / 2, la + dlat / 2))
            idx.append(i * len(lon) + j)
    return GridWeights(lat, lon, cell_weights(cells, idx, min_cover=min_cover))


def cell_weights(cells: list, idx: list[int], min_cover: float = 0.0) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """{unit: (flat cell idx, weights)} for arbitrary lon/lat cell polygons.

    min_cover = 0: every unit gets weights (a unit outside / smaller than the grid takes
    its nearest cell). min_cover > 0: units whose area is covered by the grid less than
    that fraction are left out (used for datasets that only cover part of the study area).
    """
    tree = STRtree(cells)
    extent = shapely.union_all(cells) if min_cover > 0 else None
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for u in load_units():
        if extent is not None and u.geom.intersection(extent).area < min_cover * u.geom.area:
            continue
        hits = tree.query(u.geom, predicate="intersects")
        flat, w = [], []
        for h in hits:
            inter = cells[h].intersection(u.geom)
            if inter.area > 0:
                flat.append(idx[h])
                w.append(inter.area * math.cos(math.radians(cells[h].centroid.y)))
        if not flat:  # unit smaller than / outside grid: nearest cell
            c = u.geom.representative_point()
            h = int(np.argmin([cells[k].distance(c) for k in range(len(cells))]))
            flat, w = [idx[h]], [1.0]
        w_arr = np.asarray(w)
        out[u.id] = (np.asarray(flat), w_arr / w_arr.sum())
    return out


def coverage(extent) -> dict[str, float]:
    """Share of each unit's area inside a lon/lat polygon (data extent)."""
    return {u.id: u.geom.intersection(extent).area / u.geom.area for u in load_units()}


def aggregate(values: np.ndarray, gw: GridWeights, min_valid: float = 0.0) -> dict[str, np.ndarray]:
    """values[..., lat, lon] -> {unit: values[...]} weighted mean, NaN-aware.

    min_valid: a unit value is only kept when cells holding data carry at least this share
    of the unit's weight (otherwise a few edge cells would stand in for the whole unit)."""
    flat = values.reshape(values.shape[:-2] + (-1,))
    out = {}
    for uid, (cells, w) in gw.units.items():
        v = flat[..., cells]
        ok = ~np.isnan(v)
        ww = np.where(ok, w, 0.0)
        s = ww.sum(axis=-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[uid] = np.where((s > 0) & (s >= min_valid - 1e-9), np.nansum(np.where(ok, v, 0) * ww, axis=-1) / s, np.nan)
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


def merge_existing(name: str, keys: list[str], units: dict[str, list]) -> tuple[list[str], dict[str, list], list[str]]:
    """Keep periods of an existing data/nasa/<name>.json that this build could not rebuild.

    The raw folders differ between machines (one has 2015–2025 AOI clips, another the
    2021–2026 downloads). Rebuilding from a partial raw set must not throw away periods
    that an earlier, fuller build produced. Periods present in both are taken from the new
    build. Returns (keys, units, carried-over keys).
    """
    path = DATA / "nasa" / f"{name}.json"
    if not path.exists():
        return keys, units, []
    old = json.loads(path.read_text(encoding="utf-8"))
    new_pos = {k: i for i, k in enumerate(keys)}
    carried = [k for k in old["keys"] if k not in new_pos]
    if not carried:
        return keys, units, []
    old_pos = {k: i for i, k in enumerate(old["keys"])}
    all_keys = sorted(set(keys) | set(carried))
    out = {}
    for uid in sorted(set(units) | set(old["units"])):
        new_v, old_v = units.get(uid), old["units"].get(uid)
        row = []
        for k in all_keys:
            if k in new_pos:
                row.append(new_v[new_pos[k]] if new_v is not None else None)
            else:
                row.append(old_v[old_pos[k]] if old_v is not None else None)
        out[uid] = row
    return all_keys, out, carried


def month_keys(start_year: int, start_month: int, n: int) -> list[str]:
    out, y, m = [], start_year, start_month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out
