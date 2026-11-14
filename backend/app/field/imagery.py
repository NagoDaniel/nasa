"""Field-level vegetation (NDVI) from NASA HLS (30 m) and Sentinel-2 L2A (10 m).

For a drawn field the backend searches the public STAC catalogues, reads only the small
pixel window under the field from each cloud-optimised GeoTIFF, masks clouds with each
product's own quality layer, and summarises the pixels whose centre lies in the field.

- HLS v2.0 (HLSL30 + HLSS30, NASA LP DAAC, needs an Earthdata login: ~/.netrc or
  S2F_EARTHDATA_TOKEN). Red = B04, NIR = B05 (Landsat) / B8A (Sentinel-2). Fmask bits
  1 cloud, 2 adjacent to cloud/shadow, 3 cloud shadow, 4 snow/ice are masked.
- Sentinel-2 L2A (Element 84 Earth Search on AWS, no account). Red = B04, NIR = B08 at
  10 m; SCL (20 m) classes 4 vegetation, 5 bare soil, 6 water are kept, the rest masked.

Every observation keeps its date, sensor, tile, scene cloud cover, pixel count and the
share of field pixels that were clear. Nothing is gap-filled or interpolated.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field as dfield
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import transform as shp_transform

from ..config import BASE_DIR, settings
from .geom import describe, geom_key

log = logging.getLogger(__name__)

CACHE_DIR = BASE_DIR / ".cache" / "fields"
VERSION = 2  # bump to invalidate cached results when the method changes
SEASON_TTL_S = 12 * 3600
SKIP_CLOUD = 80.0  # scenes this cloudy (whole ~110 km tile) are listed as cloudy without reading pixels
MAX_SEASON_OBS = 250  # per source (a full season is ~150 images incl. cloudy ones)
PEAK_MONTHS = ("06-01", "07-31")
PEAK_YEARS = 5
PEAK_CANDIDATES = 3
MAX_OVERLAY_PX = 1600
CLEAR_PCT, PARTLY_PCT = 90.0, 50.0
SPIKE_DAYS, SPIKE_NDVI = 12, 0.25  # undetected-cloud check, see flag_spikes()

HLS_STAC = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search"
S2_STAC = "https://earth-search.aws.element84.com/v1/search"

SOURCES = {
    "hls": {
        "label": "NASA HLS v2.0 — Harmonized Landsat 8/9 + Sentinel-2 (LP DAAC)",
        "short": "HLS", "resolution_m": 30, "cloud_mask": "Fmask (cloud, cloud shadow, adjacent, snow masked)",
        "collections": ["HLSS30_2.0", "HLSL30_2.0"], "nasa": True,
    },
    "s2": {
        "label": "Copernicus Sentinel-2 L2A (ESA), via Element 84 Earth Search on AWS",
        "short": "Sentinel-2", "resolution_m": 10, "cloud_mask": "Scene classification (SCL): only vegetation, bare soil, water kept",
        "collections": ["sentinel-2-l2a"], "nasa": False,
    },
}


# ----------------------------------------------------------------------------- GDAL / auth
def _gdal_env() -> dict[str, str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    env = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff",
        "GDAL_HTTP_COOKIEFILE": str(CACHE_DIR / "gdal_cookies.txt"),
        "GDAL_HTTP_COOKIEJAR": str(CACHE_DIR / "gdal_cookies.txt"),
        "GDAL_HTTP_MAX_RETRY": "3",
        "GDAL_HTTP_RETRY_DELAY": "1",
        "GDAL_HTTP_TIMEOUT": "40",
        "VSI_CACHE": "TRUE",
        "GDAL_INGESTED_BYTES_AT_OPEN": "65536",  # read the COG header in one request
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MULTIPLEX": "YES",
        "GDAL_HTTP_VERSION": "2",
        "AWS_NO_SIGN_REQUEST": "YES",
    }
    if settings.earthdata_token:
        env["GDAL_HTTP_HEADERS"] = f"Authorization: Bearer {settings.earthdata_token.get_secret_value()}"
    else:
        env["GDAL_HTTP_NETRC"] = "YES"
    return env


def earthdata_configured() -> bool:
    if settings.earthdata_token:
        return True
    netrc = Path(os.environ.get("NETRC", Path.home() / ".netrc"))
    try:
        return "urs.earthdata.nasa.gov" in netrc.read_text()
    except OSError:
        return False


# ----------------------------------------------------------------------------- search
@dataclass
class Obs:
    source: str
    item_id: str
    dt: str
    day: str
    sensor: str
    tile: str
    cloud: float | None
    red: str
    nir: str
    mask: str
    scale: float = 0.0001
    offset: float = 0.0
    footprint: Any = None
    result: dict = dfield(default_factory=dict)
    overlay: dict | None = None


def _stac_search(url: str, body: dict, client: httpx.Client, max_items: int = 400) -> list[dict]:
    items: list[dict] = []
    r = client.post(url, json=body)
    while True:
        r.raise_for_status()
        j = r.json()
        items += j.get("features", [])
        nxt = next((l for l in j.get("links", []) if l.get("rel") == "next"), None)
        if not nxt or len(items) >= max_items:
            return items
        if (nxt.get("method") or "GET").upper() == "POST":
            nb = nxt.get("body") or {}
            r = client.post(nxt["href"], json={**body, **nb} if nxt.get("merge") else (nb or body))
        else:
            r = client.get(nxt["href"])


def _hls_obs(it: dict) -> Obs | None:
    a = it["assets"]
    parts = it["id"].split(".")  # HLS.S30.T34TGS.2026182T092031.v2.0
    sensor = parts[1]
    nir = "B8A" if sensor == "S30" else "B05"
    if not all(k in a for k in ("B04", nir, "Fmask")):
        return None
    dt = it["properties"]["datetime"]
    return Obs("hls", it["id"], dt, dt[:10], "Sentinel-2 (HLS S30)" if sensor == "S30" else "Landsat 8/9 (HLS L30)",
               parts[2], it["properties"].get("eo:cloud_cover"), a["B04"]["href"], a[nir]["href"], a["Fmask"]["href"],
               footprint=shape(it["geometry"]))


def _s2_obs(it: dict) -> Obs | None:
    a = it["assets"]
    if not all(k in a for k in ("red", "nir", "scl")):
        return None
    rb = (a["red"].get("raster:bands") or [{}])[0]
    p = it["properties"]
    # Earth Search already applied the L2A BOA offset to the pixel values when this flag is
    # true, while still listing the original −0.1 offset; applying it again makes every pixel negative.
    offset = 0.0 if p.get("earthsearch:boa_offset_applied") else float(rb.get("offset", 0.0))
    dt = p["datetime"]
    tile = it["id"].split("_")[1] if "_" in it["id"] else ""
    return Obs("s2", it["id"], dt, dt[:10], (p.get("platform") or "sentinel-2").replace("sentinel", "Sentinel"), tile,
               p.get("eo:cloud_cover"), a["red"]["href"], a["nir"]["href"], a["scl"]["href"],
               scale=float(rb.get("scale", 0.0001)), offset=offset, footprint=shape(it["geometry"]))


def search(source: str, poly: Polygon, start: str, end: str, client: httpx.Client) -> list[Obs]:
    body = {"collections": SOURCES[source]["collections"], "bbox": list(poly.bounds),
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z", "limit": 100}
    items = _stac_search(HLS_STAC if source == "hls" else S2_STAC, body, client)
    conv = _hls_obs if source == "hls" else _s2_obs
    obs = [o for it in items if (o := conv(it))]
    # One observation per sensor and day: overlapping tiles hold the same pixels; keep the
    # tile that contains the whole field (else the one covering most of it).
    best: dict[tuple[str, str], Obs] = {}
    for o in obs:
        k = (o.sensor, o.day)
        cover = o.footprint.intersection(poly).area if o.footprint is not None else 0
        if k not in best or cover > best[k].footprint.intersection(poly).area:
            best[k] = o
    return sorted(best.values(), key=lambda o: o.dt)


# ----------------------------------------------------------------------------- reading pixels
def _ndvi_colors(nd: np.ndarray) -> np.ndarray:
    """NDVI -> RGB (brown bare soil -> yellow -> dark green)."""
    stops = np.array([-0.1, 0.15, 0.35, 0.55, 0.75, 0.9])
    cols = np.array([[140, 81, 10], [216, 179, 101], [246, 232, 195], [166, 217, 106], [26, 150, 65], [0, 90, 40]], float)
    x = np.clip(nd, stops[0], stops[-1])
    rgb = np.stack([np.interp(x, stops, cols[:, c]) for c in range(3)], axis=-1)
    return rgb.astype(np.uint8)


def _png(rgba: np.ndarray) -> str:
    from rasterio.io import MemoryFile

    h, w, _ = rgba.shape
    with MemoryFile() as mf:
        with mf.open(driver="PNG", width=w, height=h, count=4, dtype="uint8") as dst:
            dst.write(np.moveaxis(rgba, -1, 0))
        return "data:image/png;base64," + base64.b64encode(mf.read()).decode()


def read_obs(o: Obs, poly: Polygon, want_overlay: bool) -> None:
    """Fill o.result (and o.overlay) with the NDVI summary of the field pixels."""
    import rasterio
    from pyproj import Transformer
    from rasterio.features import geometry_mask
    from rasterio.windows import Window, from_bounds

    res_m = SOURCES[o.source]["resolution_m"]
    with rasterio.Env(**_gdal_env()):
        with rasterio.open(o.red) as rsrc:
            to_utm = Transformer.from_crs("EPSG:4326", rsrc.crs, always_xy=True)
            fpoly = shp_transform(lambda x, y, z=None: to_utm.transform(x, y), poly)
            w0 = from_bounds(*fpoly.bounds, rsrc.transform)
            step = 2 if o.source == "s2" else 1  # S2: align to the 20 m SCL grid
            c0 = int(np.floor(w0.col_off / step) * step) - step
            r0 = int(np.floor(w0.row_off / step) * step) - step
            c1 = int(np.ceil((w0.col_off + w0.width) / step) * step) + step
            r1 = int(np.ceil((w0.row_off + w0.height) / step) * step) + step
            win = Window(c0, r0, c1 - c0, r1 - r0)
            tr = rsrc.window_transform(win)
            red = rsrc.read(1, window=win, boundless=True, fill_value=0).astype(float)
            crs = rsrc.crs
        with rasterio.open(o.nir) as nsrc:
            nir = nsrc.read(1, window=win, boundless=True, fill_value=0).astype(float)
        with rasterio.open(o.mask) as msrc:
            if o.source == "s2":
                mwin = Window(c0 // 2, r0 // 2, (c1 - c0) // 2, (r1 - r0) // 2)
                m = msrc.read(1, window=mwin, boundless=True, fill_value=0)
                m = np.repeat(np.repeat(m, 2, axis=0), 2, axis=1)[: red.shape[0], : red.shape[1]]
            else:
                m = msrc.read(1, window=win, boundless=True, fill_value=255)

    inside = geometry_mask([mapping(fpoly)], out_shape=red.shape, transform=tr, invert=True)
    selection = "pixel centres inside the field"
    if not inside.any():
        inside = geometry_mask([mapping(fpoly)], out_shape=red.shape, transform=tr, invert=True, all_touched=True)
        selection = "pixels touching the field (field smaller than one pixel)"

    if o.source == "hls":
        nodata = (m == 255) | (red == -9999) | (nir == -9999)
        flagged = ((m >> 1) & 0b1111) > 0  # bits 1–4: cloud, adjacent, shadow, snow/ice
        scale, offset = 0.0001, 0.0
    else:
        nodata = (m == 0) | (red == 0) | (nir == 0)
        flagged = ~np.isin(m, (4, 5, 6))
        scale, offset = o.scale, o.offset
    r = red * scale + offset
    n = nir * scale + offset
    with np.errstate(invalid="ignore", divide="ignore"):
        nd = (n - r) / (n + r)
    sane = (r > 0) & (n > 0) & (r < 1.5) & (n < 1.5) & np.isfinite(nd)
    valid = inside & ~nodata & ~flagged & sane
    n_in = int(inside.sum())
    n_nodata = int((inside & nodata).sum())
    n_valid = int(valid.sum())
    vpct = 100 * n_valid / n_in if n_in else 0.0
    if n_in == 0 or n_nodata >= 0.5 * n_in:
        status = "no_data"
    elif vpct >= CLEAR_PCT:
        status = "clear"
    elif vpct >= PARTLY_PCT:
        status = "partly_cloudy"
    else:
        status = "cloudy"
    stats = None
    if status in ("clear", "partly_cloudy") and n_valid:
        v = nd[valid]
        stats = {"mean": round(float(v.mean()), 3), "median": round(float(np.median(v)), 3),
                 "p10": round(float(np.percentile(v, 10)), 3), "p90": round(float(np.percentile(v, 90)), 3)}
    o.result = {
        "date": o.day, "datetime": o.dt, "source": o.source, "sensor": o.sensor, "tile": o.tile, "item_id": o.item_id,
        "scene_cloud_pct": None if o.cloud is None else round(float(o.cloud), 1), "status": status,
        "pixel_size_m": res_m, "pixels_in_field": n_in, "pixel_selection": selection,
        "valid_pixels": n_valid, "valid_pct": round(vpct, 1), "ndvi": stats,
    }
    if want_overlay and status == "clear" and max(red.shape) <= MAX_OVERLAY_PX:
        rgba = np.zeros(red.shape + (4,), np.uint8)
        rgba[..., :3] = _ndvi_colors(np.nan_to_num(nd))
        rgba[..., 3] = np.where(valid, 235, 0)
        rgba[inside & ~valid & ~nodata, :] = (120, 120, 120, 170)  # masked (cloud etc.) pixels inside the field: grey
        to_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        h, w = red.shape
        corners = [tr * (0, 0), tr * (w, 0), tr * (w, h), tr * (0, h)]
        o.overlay = {"image": _png(rgba), "corners": [list(map(lambda v: round(v, 7), to_ll.transform(x, y))) for x, y in corners],
                     "pixel_size_m": res_m, "date": o.day, "sensor": o.sensor,
                     "pixels_in_field": n_in}


def _skip(o: Obs) -> None:
    o.result = {"date": o.day, "datetime": o.dt, "source": o.source, "sensor": o.sensor, "tile": o.tile, "item_id": o.item_id,
                "scene_cloud_pct": round(float(o.cloud), 1), "status": "cloudy", "pixel_size_m": SOURCES[o.source]["resolution_m"],
                "pixels_in_field": None, "valid_pixels": 0, "valid_pct": None, "ndvi": None,
                "note": f"Scene ≥ {SKIP_CLOUD:.0f}% cloud: pixels not read"}


# ----------------------------------------------------------------------------- jobs
@dataclass
class Job:
    id: str
    status: str = "queued"  # queued | running | done | error
    stage: str = "queued"
    done: int = 0
    total: int = 0
    result: dict | None = None
    error: str | None = None
    created: float = dfield(default_factory=time.time)

    def public(self) -> dict:
        return {"job_id": self.id, "status": self.status, "stage": self.stage,
                "progress": {"done": self.done, "total": self.total}, "error": self.error, "result": self.result}


_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_job_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="field-job")
_read_pool = ThreadPoolExecutor(max_workers=24, thread_name_prefix="field-read")
_search_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="field-search")
_source_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="field-source")


def _season(today: date) -> tuple[int, str, str]:
    year = today.year if today.month >= 4 else today.year - 1
    end = min(today, date(year, 11, 30))
    return year, f"{year}-03-01", end.isoformat()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"veg_{VERSION}_{key}.json"


def _peak_path(key: str, source: str, year: int) -> Path:
    return CACHE_DIR / "peaks" / f"{VERSION}_{key}_{source}_{year}.json"


def start(poly: Polygon) -> Job:
    key = geom_key(poly)
    with _lock:
        for k in [k for k, j in _jobs.items() if time.time() - j.created > 3600]:
            del _jobs[k]
        j = _jobs.get(key)
        if j and j.status in ("queued", "running"):
            return j
        cp = _cache_path(key)
        if cp.exists() and time.time() - cp.stat().st_mtime < SEASON_TTL_S:
            j = Job(key, status="done", stage="cached", result=json.loads(cp.read_text()))
            _jobs[key] = j
            return j
        j = Job(key)
        _jobs[key] = j
    _job_pool.submit(_run, j, poly)
    return j


def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def _read_all(job: Job, obs: list[Obs], poly: Polygon, overlay_ids: set[str]) -> None:
    def one(o: Obs) -> None:
        try:
            read_obs(o, poly, o.item_id in overlay_ids)
        except Exception as e:  # noqa: BLE001
            log.warning("field read failed %s: %s", o.item_id, str(e)[:200])
            o.result = {"date": o.day, "datetime": o.dt, "source": o.source, "sensor": o.sensor, "tile": o.tile,
                        "item_id": o.item_id, "scene_cloud_pct": o.cloud, "status": "error", "ndvi": None,
                        "pixel_size_m": SOURCES[o.source]["resolution_m"],
                        "note": "Could not read this image" + (" (Earthdata login?)" if o.source == "hls" else "")}
        finally:
            with _lock:
                job.done += 1

    list(_read_pool.map(one, obs))


def _run(job: Job, poly: Polygon) -> None:
    job.status = "running"
    try:
        key = job.id
        today = datetime.now(timezone.utc).date()
        year, s_start, s_end = _season(today)
        srcs = [s for s in SOURCES if s != "hls" or earthdata_configured()]
        out_sources: dict[str, Any] = {}
        season_obs: dict[str, list[Obs]] = {}
        peak_obs: dict[tuple[str, int], list[Obs]] = {}
        peak_cached: dict[tuple[str, int], dict] = {}
        job.stage = "searching catalogues"
        with httpx.Client(timeout=60, headers={"User-Agent": "space2feed-dashboard"}) as client:
            def season_search(s: str):
                return s, search(s, poly, s_start, s_end, client)[-MAX_SEASON_OBS:]

            def peak_search(s: str, y: int):
                cand = search(s, poly, f"{y}-{PEAK_MONTHS[0]}", f"{y}-{PEAK_MONTHS[1]}", client)
                cand = sorted([o for o in cand if o.cloud is None or o.cloud < SKIP_CLOUD], key=lambda o: o.cloud or 0)
                return (s, y), cand[:PEAK_CANDIDATES]

            futs = {s: _search_pool.submit(season_search, s) for s in srcs}
            pfuts = {}
            for s in srcs:
                for y in range(year - PEAK_YEARS, year):
                    pp = _peak_path(key, s, y)
                    if pp.exists():
                        peak_cached[(s, y)] = json.loads(pp.read_text())
                    else:
                        pfuts[(s, y)] = _search_pool.submit(peak_search, s, y)
            for s, f in futs.items():
                try:
                    season_obs[s] = f.result()[1]
                except Exception as e:  # noqa: BLE001
                    log.warning("STAC search failed for %s: %s", s, str(e)[:200])
                    out_sources[s] = {**{k: v for k, v in SOURCES[s].items() if k != "collections"},
                                      "status": "error", "note": "Catalogue search failed; try again later."}
            for k, f in pfuts.items():
                try:
                    peak_obs[k] = f.result()[1]
                except Exception:  # noqa: BLE001
                    peak_obs[k] = []

        job.stage = "reading pixels"
        job.total = sum(
            sum(1 for o in season_obs.get(src, []) if o.cloud is None or o.cloud < SKIP_CLOUD)
            + sum(len(v) for (ps, _), v in peak_obs.items() if ps == src)
            for src in srcs)
        if "hls" not in srcs:
            out_sources["hls"] = {**{k: v for k, v in SOURCES["hls"].items() if k != "collections"}, "status": "unavailable",
                                  "note": "No Earthdata login configured on the server (~/.netrc or S2F_EARTHDATA_TOKEN)."}
        pending = [src for src in srcs if src in season_obs]
        job.result = _result(poly, year, s_start, s_end, out_sources, pending)

        def process(src: str) -> None:
            entry = _source_entry(job, src, season_obs[src], peak_obs, peak_cached, poly, key, year)
            with _lock:
                out_sources[src] = entry
                pending.remove(src)
                job.result = _result(poly, year, s_start, s_end, out_sources, list(pending))

        list(_source_pool.map(process, list(pending)))
        result = _result(poly, year, s_start, s_end, out_sources, [])
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_text(json.dumps(result))
        job.result = result
        job.stage = "done"
        job.status = "done"
    except Exception as e:  # noqa: BLE001
        log.exception("field vegetation job failed")
        job.status = "error"
        job.error = "Could not load imagery for this field. Try again in a minute."
        job.stage = str(type(e).__name__)


def flag_spikes(sources: dict) -> None:
    """Mark values that jump away from the clear images just before and after them (any
    source, within SPIKE_DAYS) as possible undetected cloud / haze. Masks miss thin cloud
    and fog; such an image reads as a sudden NDVI drop that the neighbours do not show."""
    pts = []
    for s in sources.values():
        for o in s.get("observations") or []:
            if o.get("ndvi") and o["status"] in ("clear", "partly_cloudy", "suspect"):
                if o["status"] == "suspect":  # re-evaluate from scratch on every call
                    o["status"] = o.pop("status_before_check", "clear")
                    o.pop("note", None)
                pts.append((date.fromisoformat(o["date"]), o))
    pts.sort(key=lambda x: x[0])
    for i, (d, o) in enumerate(pts):
        v = o["ndvi"]["median"]
        prev = next((p for p in reversed(pts[:i]) if p[0] < d), None)
        nxt = next((p for p in pts[i + 1:] if p[0] > d), None)
        if not prev or not nxt or (d - prev[0]).days > SPIKE_DAYS or (nxt[0] - d).days > SPIKE_DAYS:
            continue
        a, b = v - prev[1]["ndvi"]["median"], v - nxt[1]["ndvi"]["median"]
        if a * b > 0 and min(abs(a), abs(b)) > SPIKE_NDVI:
            o["status_before_check"] = o["status"]
            o["status"] = "suspect"
            o["note"] = (f"NDVI {v:.2f} differs by more than {SPIKE_NDVI} from the clear images on {prev[0]} "
                         f"({prev[1]['ndvi']['median']:.2f}) and {nxt[0]} ({nxt[1]['ndvi']['median']:.2f}): possible undetected cloud or haze")


def finalize(sources: dict) -> dict:
    """Spike check, status counts and the latest clear image (with its map overlay) per source."""
    out = {k: dict(v) for k, v in sources.items()}
    flag_spikes(out)
    for v in out.values():
        if v.get("status") != "ok":
            continue
        overlays = v.pop("_overlays", {}) or {}
        counts: dict[str, int] = {}
        for r in v["observations"]:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        v["counts"] = counts
        clear = [r for r in v["observations"] if r["status"] == "clear" and r["item_id"] in overlays]
        v["latest_clear"] = {**clear[-1], "overlay": overlays[clear[-1]["item_id"]]} if clear else None
    return out


def _result(poly: Polygon, year: int, s_start: str, s_end: str, sources: dict, pending: list[str]) -> dict:
    return {
        "field": {k: v for k, v in describe(poly).items() if k != "geometry"},
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season": {"year": year, "start": s_start, "end": s_end},
        "index": "NDVI = (NIR − Red) / (NIR + Red), surface reflectance; median of the clear field pixels",
        "status_rules": {
            "clear": f"≥ {CLEAR_PCT:.0f}% of field pixels clear",
            "partly_cloudy": f"{PARTLY_PCT:.0f}–{CLEAR_PCT:.0f}% clear: value shown, flagged",
            "cloudy": f"< {PARTLY_PCT:.0f}% clear, or whole scene ≥ {SKIP_CLOUD:.0f}% cloud (pixels not read): no value",
            "no_data": "field outside the image swath / no pixels",
            "error": "image could not be read",
            "suspect": f"value jumps > {SPIKE_NDVI} away from clear images on both sides (≤ {SPIKE_DAYS} days): possible undetected cloud, flagged and not used",
        },
        "pending": pending,
        "sources": finalize(sources),
    }


def _source_entry(job: Job, src: str, obs: list[Obs], peak_obs: dict, peak_cached: dict, poly: Polygon, key: str, year: int) -> dict:
    to_read = []
    for o in obs:
        if o.cloud is not None and o.cloud >= SKIP_CLOUD:
            _skip(o)
        else:
            to_read.append(o)
    # newest first, so a current picture is ready early; overlay for the newest readable scenes
    to_read.sort(key=lambda o: o.dt, reverse=True)
    overlay_ids = {o.item_id for o in [x for x in to_read if x.cloud is None or x.cloud < 60][:10]}
    peaks_read = [o for (ps, _), lst in peak_obs.items() if ps == src for o in lst]
    _read_all(job, to_read + peaks_read, poly, overlay_ids)

    results = [o.result for o in obs]
    overlays = {o.item_id: o.overlay for o in obs if o.overlay}
    peaks = []
    for y in range(year - PEAK_YEARS, year):
        if (src, y) in peak_cached:
            peaks.append(peak_cached[(src, y)])
            continue
        rs = [o.result for o in peak_obs.get((src, y), [])]
        ok = [r for r in rs if r.get("ndvi")]
        p = {"year": y, "window": f"{PEAK_MONTHS[0]} – {PEAK_MONTHS[1]}",
             "value": round(float(np.median([r["ndvi"]["median"] for r in ok])), 3) if ok else None,
             "n_used": len(ok), "n_read": len(rs), "dates": [r["date"] for r in ok],
             "status": "ok" if ok else ("cloudy" if rs else "no_images"), "observations": rs}
        peaks.append(p)
        if rs and all(r.get("status") != "error" for r in rs):
            _peak_path(key, src, y).parent.mkdir(parents=True, exist_ok=True)
            _peak_path(key, src, y).write_text(json.dumps(p))
    return {
        **{k: v for k, v in SOURCES[src].items() if k != "collections"},
        "status": "ok", "observations": results, "peaks": peaks, "_overlays": overlays,
    }
