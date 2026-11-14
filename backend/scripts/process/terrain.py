"""SRTM GL1 elevation / slope + ESA WorldCover 2021 land cover -> static per-unit record.

Raw (<repo>/data, see dataset_dani.md):
  srtm/<tile>.SRTMGL1.hgt.zip   six 1° tiles, 22–25 °E × 45–47 °N, 1 arc-second (~30 m)
  worldcover/..._<tile>_Map.tif  two 3° tiles, 21–27 °E × 45–48 °N, 10 m

Terrain: slope from the 30 m DEM (central differences, metres per pixel from latitude);
WorldCover is read on the same 30 m grid (nearest) to split statistics into "all land"
and "cropland" (class 40). Land cover shares come from WorldCover read at ~90 m over its
whole extent. A unit is only reported when the tiles cover ≥ MIN_COVER of its area.
Output: data/land/terrain.json.
"""

from __future__ import annotations

import re
import zipfile

import numpy as np
import rasterio
from affine import Affine
from rasterio.windows import from_bounds
from shapely.geometry import box
from shapely.ops import unary_union

from common import coverage, extra, load_units, write_json
from zonal import label_raster

N = 3600  # SRTM pixels per degree (the 3601st row/col duplicates the next tile)
MIN_COVER = 0.95
STEEP_PCT = 10.0
WC_CLASSES = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up",
              60: "bare / sparse vegetation", 70: "snow and ice", 80: "permanent water", 90: "herbaceous wetland",
              95: "mangroves", 100: "moss and lichen"}
WC_TILES = ["N45E021", "N45E024"]
M_PER_DEG = 111_320.0


def _srtm_tiles():
    for f in sorted(extra("srtm").glob("*.SRTMGL1.hgt.zip")):
        m = re.match(r"([NS])(\d{2})([EW])(\d{3})", f.name)
        la = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
        lo = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
        yield la, lo, f


def _read_hgt(f) -> np.ndarray:
    with zipfile.ZipFile(f) as z:
        name = next(n for n in z.namelist() if n.endswith(".hgt"))
        a = np.frombuffer(z.read(name), dtype=">i2").reshape(3601, 3601).astype(np.float32)
    a[a == -32768] = np.nan
    return a


def _worldcover(lo0: float, la0: float, lo1: float, la1: float, shape: tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=np.uint8)
    for t in WC_TILES:
        f = extra(f"worldcover/ESA_WorldCover_10m_2021_v200_{t}_Map.tif")
        if not f.exists():
            continue
        with rasterio.open(f) as src:
            b = src.bounds
            if b.left > lo0 or b.right < lo1 or b.bottom > la0 or b.top < la1:
                continue  # the 1° SRTM tiles never straddle the two WorldCover tiles
            out = src.read(1, window=from_bounds(lo0, la0, lo1, la1, src.transform), out_shape=shape)
    return out


def terrain() -> tuple[dict, list]:
    tiles = list(_srtm_tiles())
    if not tiles:
        return {}, []
    communes = {u.id: u for u in load_units() if u.kind == "commune"}
    keys = ["n", "elev", "slope", "steep", "cn", "cslope", "csteep"]
    acc = {uid: dict.fromkeys(keys, 0.0) for uid in communes}
    for la, lo, f in tiles:
        dem = _read_hgt(f)
        lat_c = la + 1 - (np.arange(3601) + 0.5) / N
        dy = M_PER_DEG / N
        dx = (M_PER_DEG / N) * np.cos(np.radians(lat_c))[:, None]
        gy, gx = np.gradient(dem)
        slope = 100 * np.hypot(gx / dx, gy / dy)  # percent
        dem, slope = dem[:N, :N], slope[:N, :N]
        tr = Affine(1 / N, 0, lo, 0, -1 / N, la + 1)
        lab, names = label_raster(tr, (N, N))
        wc = _worldcover(lo, la, lo + 1, la + 1, (N, N))
        ok = (lab > 0) & np.isfinite(dem) & np.isfinite(slope)
        L = lab[ok]
        crop = wc[ok] == 40
        s = slope[ok]
        nb = max(names) + 1
        parts = {
            "n": np.bincount(L, minlength=nb),
            "elev": np.bincount(L, weights=dem[ok], minlength=nb),
            "slope": np.bincount(L, weights=s, minlength=nb),
            "steep": np.bincount(L, weights=(s >= STEEP_PCT).astype(float), minlength=nb),
            "cn": np.bincount(L, weights=crop.astype(float), minlength=nb),
            "cslope": np.bincount(L, weights=np.where(crop, s, 0), minlength=nb),
            "csteep": np.bincount(L, weights=(crop & (s >= STEEP_PCT)).astype(float), minlength=nb),
        }
        for i, uid in names.items():
            for k in keys:
                acc[uid][k] += float(parts[k][i])
        print(f"  SRTM {f.name.split('.')[0]}: done")
    extent = unary_union([box(lo, la, lo + 1, la + 1) for la, lo, _ in tiles])
    cover = coverage(extent)
    # counties = sums of their communes, only when the whole county is covered
    by_county: dict[str, list] = {}
    for uid in communes:
        by_county.setdefault(uid.split("-")[0], []).append(uid)
    for c, ids in by_county.items():
        acc[c] = {k: sum(acc[i][k] for i in ids) for k in keys}
    out = {}
    for uid, a in acc.items():
        if cover.get(uid, 0) < MIN_COVER or a["n"] == 0:
            continue
        rec = {
            "elevation_m": round(a["elev"] / a["n"]),
            "slope_pct": round(a["slope"] / a["n"], 1),
            "steep_share_pct": round(100 * a["steep"] / a["n"], 1),
        }
        if a["cn"] >= 100:  # ≥ ~9 ha of cropland on the 30 m grid
            rec["cropland_slope_pct"] = round(a["cslope"] / a["cn"], 1)
            rec["cropland_steep_share_pct"] = round(100 * a["csteep"] / a["cn"], 1)
        out[uid] = rec
    bounds = extent.bounds
    return out, [round(b, 2) for b in bounds]


def landcover() -> dict:
    step = 1 / 1200  # ~90 m × 65 m
    shares: dict[str, np.ndarray] = {}
    extents = []
    for t in WC_TILES:
        f = extra(f"worldcover/ESA_WorldCover_10m_2021_v200_{t}_Map.tif")
        if not f.exists():
            continue
        with rasterio.open(f) as src:
            b = src.bounds
            h, w = round((b.top - b.bottom) / step), round((b.right - b.left) / step)
            a = src.read(1, out_shape=(h, w))
        extents.append(box(b.left, b.bottom, b.right, b.top))
        tr = Affine(step, 0, b.left, 0, -step, b.top)
        lab, names = label_raster(tr, (h, w))
        ok = (lab > 0) & (a > 0)
        L, C = lab[ok].astype(np.int64), a[ok].astype(np.int64)
        nb = max(names) + 1
        counts = np.bincount(L * 101 + C, minlength=nb * 101).reshape(nb, 101)
        for i, uid in names.items():
            shares[uid] = shares.get(uid, np.zeros(101)) + counts[i]
    if not extents:
        return {}
    cover = coverage(unary_union(extents))
    by_county: dict[str, list] = {}
    for uid in list(shares):
        by_county.setdefault(uid.split("-")[0], []).append(uid)
    for c, ids in by_county.items():
        shares[c] = sum(shares[i] for i in ids)
    out = {}
    for uid, cnt in shares.items():
        if cover.get(uid, 0) < MIN_COVER or cnt.sum() == 0:
            continue
        tot = cnt.sum()
        out[uid] = {str(k): round(100 * cnt[k] / tot, 1) for k in WC_CLASSES if cnt[k] > 0}
    return out


def main() -> None:
    load_units()
    ter, srtm_bounds = terrain()
    lc = landcover()
    units = {}
    for uid in sorted(set(ter) | set(lc)):
        rec = dict(ter.get(uid, {}))
        if uid in lc:
            rec["landcover_pct"] = lc[uid]
        units[uid] = rec
    ab = units.get("AB", {})
    print(f"  terrain units {len(ter)}, land-cover units {len(lc)}; Alba: {ab.get('elevation_m')} m, slope {ab.get('slope_pct')} %, "
          f"cropland slope {ab.get('cropland_slope_pct')} %, cropland {ab.get('landcover_pct', {}).get('40')} %")
    write_json(
        "land/terrain.json",
        {
            "sources": {
                "terrain": "NASA SRTM GL1 v003 (SRTMGL1, LP DAAC), 1 arc-second DEM, acquired Feb 2000",
                "landcover": "ESA WorldCover 10 m 2021 v200 (CC BY 4.0, © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021))",
            },
            "resolution": {"terrain": "30 m", "landcover": "10 m map, counted at ~90 m"},
            "extent": {"terrain": srtm_bounds, "landcover": [21, 45, 27, 48]},
            "steep_threshold_pct": STEEP_PCT,
            "classes": {str(k): v for k, v in WC_CLASSES.items()},
            "confidence": {
                "county": "high",
                "commune": "high",
                "note": f"Only units covered ≥ {MIN_COVER:.0%} by the downloaded tiles are listed (terrain: 22–25 °E × 45–47 °N; land cover: 21–27 °E × 45–48 °N). "
                "Slope is in percent (rise / run × 100) from the 30 m SRTM DEM; cropland = WorldCover class 40. "
                f"Above ~{STEEP_PCT:.0f} % slope, water erosion on bare soil rises steeply, so steep cropland benefits most from winter cover and contour work.",
            },
            "units": units,
        },
    )


if __name__ == "__main__":
    main()
