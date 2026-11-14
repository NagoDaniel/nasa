"""Place search for the area picker: street, village or place name -> map location + commune.

Uses OpenStreetMap Nominatim (https://nominatim.org), limited to the study area. Their usage
policy: at most 1 request per second, an identifying User-Agent, no search-as-you-type, and
OpenStreetMap attribution. So the frontend only calls this on Enter / button; results are
cached; one global request per second; the User-Agent names the app, never the user.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from ..assistant.guard import RateLimiter, client_key, sanitize
from ..field.geom import commune_at

router = APIRouter(tags=["geocode"])
URL = "https://nominatim.openstreetmap.org/search"
UA = "SPACE2FEED/0.1 (NASA Space Apps 2026 demo; field-planning dashboard)"
VIEWBOX = "20.6,47.7,25.4,44.4"  # study area (lon/lat), results are bounded to it
limiter = RateLimiter(10, 200, 0)
_lock = threading.Lock()
_last = [0.0]
_cache: OrderedDict[str, list[dict]] = OrderedDict()
CACHE_MAX = 500


def _short(item: dict) -> tuple[str, str]:
    a = item.get("address") or {}
    name = item.get("name") or item.get("display_name", "").split(",")[0]
    place = a.get("village") or a.get("town") or a.get("city") or a.get("hamlet") or a.get("municipality") or ""
    county = a.get("county") or ""
    detail = ", ".join(x for x in (place if place != name else "", county) if x)
    return name, detail


def _nominatim(q: str, lang: str) -> list[dict]:
    key = f"{lang}|{q.lower()}"
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    with _lock:  # one request per second for the whole server
        wait = 1.0 - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = httpx.get(URL, params={"q": q, "format": "jsonv2", "countrycodes": "ro", "viewbox": VIEWBOX, "bounded": 1,
                                       "limit": 8, "addressdetails": 1},
                          headers={"User-Agent": UA, "Accept-Language": f"{lang},ro,en"}, timeout=8)
        finally:
            _last[0] = time.monotonic()
    if r.status_code != 200:
        raise HTTPException(502, "Place search is not available right now")
    out, seen = [], set()
    for it in r.json():
        lon, lat = float(it["lon"]), float(it["lat"])
        bb = it.get("boundingbox")  # [south, north, west, east]
        name, detail = _short(it)
        if (name, detail) in seen:  # one street = many OSM segments
            continue
        seen.add((name, detail))
        out.append({
            "name": name, "detail": detail, "type": it.get("type") or it.get("category"),
            "lon": lon, "lat": lat,
            "bbox": [float(bb[2]), float(bb[0]), float(bb[3]), float(bb[1])] if bb else None,
            "commune": commune_at(lon, lat),
        })
    _cache[key] = out
    if len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)
    return out


@router.get("/geocode")
def geocode(request: Request, q: str = Query(min_length=2, max_length=100), lang: str = "ro") -> dict[str, Any]:
    """Search streets / villages / places in the study area (OpenStreetMap Nominatim)."""
    ok, retry = limiter.hit(client_key(request.client.host if request.client else None, request.headers.get("x-forwarded-for")))
    if not ok:
        raise HTTPException(429, "Too many searches, please wait a moment", headers={"Retry-After": str(retry)})
    text = sanitize(q, 100)
    if len(text) < 2:
        raise HTTPException(422, "Type at least 2 characters")
    try:
        results = _nominatim(text, "en" if lang == "en" else "ro")
    except httpx.HTTPError:
        raise HTTPException(502, "Place search is not available right now")
    return {"query": text, "results": results, "attribution": "Search: © OpenStreetMap contributors, Nominatim"}
