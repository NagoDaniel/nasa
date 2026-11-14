"""Drawn field geometry: validation, geodesic area, and which commune it lies in."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import shapely
from fastapi import HTTPException
from pyproj import Geod
from shapely.geometry import Polygon, mapping, shape
from shapely.strtree import STRtree

from ..json_store import store
from ..i18n import num, t

GEOD = Geod(ellps="WGS84")
MIN_HA = 0.5  # below this even 10 m imagery has < 50 pixels; the UI warns under 1 ha
MAX_HA = 5000.0  # 50 km²: bigger selections make imagery reads slow
MAX_VERTICES = 200
RO_BBOX = (20.2, 43.6, 29.8, 48.3)


def bad(msg: str) -> HTTPException:
    return HTTPException(422, msg)


def parse(geometry: dict[str, Any]) -> Polygon:
    """GeoJSON Polygon (lon/lat, one ring) -> valid shapely polygon, or 422."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise bad(t("fd_not_polygon"))
    rings = geometry.get("coordinates")
    if not isinstance(rings, list) or len(rings) != 1 or not isinstance(rings[0], list):
        raise bad(t("fd_one_ring"))
    ring = rings[0]
    if not 4 <= len(ring) <= MAX_VERTICES + 1:
        raise bad(t("fd_corners", n=MAX_VERTICES))
    pts = []
    for p in ring:
        if not (isinstance(p, list) and len(p) >= 2 and all(isinstance(c, (int, float)) and math.isfinite(c) for c in p[:2])):
            raise bad(t("fd_bad_coord"))
        lon, lat = float(p[0]), float(p[1])
        if not (RO_BBOX[0] <= lon <= RO_BBOX[2] and RO_BBOX[1] <= lat <= RO_BBOX[3]):
            raise bad(t("fd_romania"))
        pts.append((round(lon, 7), round(lat, 7)))
    poly = Polygon(pts)
    if not poly.is_valid:
        raise bad(t("fd_crosses"))
    return poly


def area_ha(poly: Polygon) -> float:
    a, _ = GEOD.geometry_area_perimeter(poly)
    return abs(a) / 10_000


def perimeter_m(poly: Polygon) -> float:
    return abs(GEOD.geometry_area_perimeter(poly)[1])


def check_size(poly: Polygon) -> float:
    ha = area_ha(poly)
    if ha < MIN_HA:
        raise bad(t("fd_min", ha=num(ha, 2), min=num(MIN_HA, 1)))
    if ha > MAX_HA:
        raise bad(t("fd_max", ha=num(ha), max=num(MAX_HA)))
    return ha


_communes: dict = {"src": None}


def _commune_index() -> dict:
    fc = store.get("geo/communes.geojson.json")
    if _communes["src"] is not fc:
        geoms = [shape(f["geometry"]) for f in fc["features"]]
        _communes.update(src=fc, geoms=geoms, props=[f["properties"] for f in fc["features"]], tree=STRtree(geoms))
    return _communes


def commune_at(lon: float, lat: float) -> dict | None:
    """Study-area commune containing a point (None outside the study area)."""
    from shapely.geometry import Point

    idx = _commune_index()
    pt = Point(lon, lat)
    for i in idx["tree"].query(pt, predicate="intersects"):
        p = idx["props"][i]
        return {"id": p["id"], "name": p["name"], "county": p["county"], "county_name": p["county_name"]}
    return None


def commune_of(poly: Polygon) -> dict | None:
    """Study-area commune holding most of the field (None outside the study area)."""
    fc = store.get("geo/communes.geojson.json")
    if _communes["src"] is not fc:
        geoms = [shape(f["geometry"]) for f in fc["features"]]
        _communes.update(src=fc, geoms=geoms, props=[f["properties"] for f in fc["features"]], tree=STRtree(geoms))
    best, best_a = None, 0.0
    for i in _communes["tree"].query(poly, predicate="intersects"):
        a = _communes["geoms"][i].intersection(poly).area
        if a > best_a:
            best, best_a = _communes["props"][i], a
    if best is None:
        return None
    return {"id": best["id"], "name": best["name"], "county": best["county"], "county_name": best["county_name"],
            "share_pct": round(100 * best_a / poly.area, 1)}


def describe(poly: Polygon) -> dict[str, Any]:
    c = poly.centroid
    return {
        "area_ha": round(area_ha(poly), 2),
        "perimeter_m": round(perimeter_m(poly)),
        "centroid": [round(c.x, 6), round(c.y, 6)],
        "bbox": [round(x, 6) for x in poly.bounds],
        "commune": commune_of(poly),
        "geometry": mapping(poly),
    }


def geom_key(poly: Polygon) -> str:
    """Stable id of a geometry (for caching and job ids)."""
    norm = shapely.normalize(poly)
    coords = [[round(x, 6), round(y, 6)] for x, y in norm.exterior.coords]
    return hashlib.sha256(json.dumps(coords).encode()).hexdigest()[:20]
