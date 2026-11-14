"""Raster zonal statistics: rasterise communes once per grid, then group pixels."""

from __future__ import annotations

import numpy as np
from rasterio import features
from rasterio.warp import transform_geom
from shapely.geometry import mapping

from common import load_units


def label_raster(transform, shape, crs=None) -> tuple[np.ndarray, dict[int, str]]:
    """int32 raster: 0 = outside, i = commune i. Returns (labels, {i: commune id})."""
    communes = [u for u in load_units() if u.kind == "commune"]
    shapes = []
    for i, u in enumerate(communes, start=1):
        g = mapping(u.geom)
        if crs is not None and str(crs) != "EPSG:4326":
            g = transform_geom("EPSG:4326", crs, g)
        shapes.append((g, i))
    lab = features.rasterize(shapes, out_shape=shape, transform=transform, fill=0, dtype="int32")
    return lab, {i: u.id for i, u in enumerate(communes, start=1)}


def unit_pixel_groups(labels: np.ndarray, names: dict[int, str]) -> dict[str, np.ndarray]:
    """{unit id: flat pixel indices} for communes and (as unions) their counties."""
    flat = labels.ravel()
    order = np.argsort(flat, kind="stable")
    counts = np.bincount(flat, minlength=max(names) + 1)
    starts = np.concatenate([[0], np.cumsum(counts)])
    out: dict[str, np.ndarray] = {}
    by_county: dict[str, list[np.ndarray]] = {}
    for i, uid in names.items():
        idx = order[starts[i]:starts[i + 1]]
        out[uid] = idx
        by_county.setdefault(uid.split("-")[0], []).append(idx)
    for c, parts in by_county.items():
        out[c] = np.concatenate(parts)
    return out
