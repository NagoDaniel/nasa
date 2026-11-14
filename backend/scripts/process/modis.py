"""MODIS tile h19v04 (sinusoidal HDF4, whole study area) -> monthly series per unit.

Raw: <repo>/data/modis_ndvi (MOD13A3 monthly 1 km), modis_et (MOD16A2GF 8-day 500 m),
modis_lst (MOD11A2 8-day 1 km); 2021-11 onward. See dataset_dani.md.

Pixels are not reprojected: each pixel centre is computed from the sinusoidal grid
and dropped into a commune label raster. Values are averaged over **cropland pixels**
(≥ 50 % ESA WorldCover 2021 class 40 "cropland" inside the pixel), so forests and
mountains don't dilute the farm signal. Cropland series exist only for units that the
two downloaded WorldCover tiles (21–27 °E, 45–48 °N) cover ≥ 90 %; NDVI is also given
over all land for every unit (modis_ndvi_all).

8-day composites are spread over calendar months by day overlap: ET/PET are summed
(a month needs full coverage), LST is averaged (a month needs ≥ 50 % of its days).
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import rasterio
from affine import Affine
from pyhdf.SD import SD, SDC
from rasterio.windows import from_bounds
from shapely.geometry import box

from common import coverage, extra, load_units, month_keys, values, write_dataset
from zonal import label_raster

H, V = 19, 4
R = 6371007.181  # MODIS sinusoidal sphere radius, m
T = 1111950.5197665233  # tile size, m
X0, Y0 = -20015109.355798, 10007554.677899
BBOX = (20.6, 44.4, 25.4, 47.7)  # lon/lat box of the study area
WC_TILES = ["N45E021", "N45E024"]
WC_EXTENT = box(21, 45, 27, 48)
WC_MIN_COVER = 0.9
CROP_FRAC = 0.5
MIN_CROP_PX = {1200: 3, 2400: 12}  # ≥ ~3 km² of cropland in the unit
MIN_CLEAR = 0.3  # share of a unit's pixels that must be valid in a composite


# ----------------------------------------------------------------------------- grid
def _sin_to_lonlat(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lat = y / R
    lon = x / (R * np.cos(lat))
    return np.degrees(lon), np.degrees(lat)


def _lonlat_to_pixel(lon: np.ndarray, lat: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    la = np.radians(lat)
    x = R * np.radians(lon) * np.cos(la)
    y = R * la
    px = T / n
    col = np.floor((x - X0 - H * T) / px).astype(np.int64)
    row = np.floor((Y0 - V * T - y) / px).astype(np.int64)
    return row, col


@lru_cache(maxsize=1)
def _labels():
    """Commune label raster on a 0.0025° lon/lat grid over the study area."""
    res = 0.0025
    w, h = round((BBOX[2] - BBOX[0]) / res), round((BBOX[3] - BBOX[1]) / res)
    tr = Affine(res, 0, BBOX[0], 0, -res, BBOX[3])
    lab, names = label_raster(tr, (h, w))
    return lab, names, tr


@lru_cache(maxsize=1)
def _worldcover_crop(step: float = 0.001):
    """Yield (lon, lat, is_cropland) samples on a regular grid from the WorldCover tiles."""
    out = []
    for t in WC_TILES:
        f = extra(f"worldcover/ESA_WorldCover_10m_2021_v200_{t}_Map.tif")
        if not f.exists():
            continue
        with rasterio.open(f) as src:
            b = src.bounds
            lo0, la0 = max(b.left, BBOX[0]), max(b.bottom, BBOX[1])
            lo1, la1 = min(b.right, BBOX[2]), min(b.top, BBOX[3])
            if lo0 >= lo1 or la0 >= la1:
                continue
            nx, ny = round((lo1 - lo0) / step), round((la1 - la0) / step)
            a = src.read(1, window=from_bounds(lo0, la0, lo1, la1, src.transform), out_shape=(ny, nx))
        lon = lo0 + (np.arange(nx) + 0.5) * step
        lat = la1 - (np.arange(ny) + 0.5) * step
        out.append((lon, lat, a))
    return out


@lru_cache(maxsize=2)
def pixel_groups(n: int) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]]:
    """For an n×n h19v04 grid: (crop fraction per pixel, {unit: all-land pixel idx}, {unit: cropland pixel idx})."""
    px = T / n
    j = np.arange(n)
    x = X0 + H * T + (j + 0.5) * px
    y = Y0 - V * T - (j + 0.5) * px
    xx, yy = np.meshgrid(x, y)
    lon, lat = _sin_to_lonlat(xx, yy)
    lab, names, tr = _labels()
    c = np.floor((lon - tr.c) / tr.a).astype(np.int64)
    r = np.floor((lat - tr.f) / tr.e).astype(np.int64)
    inside = (r >= 0) & (r < lab.shape[0]) & (c >= 0) & (c < lab.shape[1])
    pix_lab = np.zeros((n, n), dtype=np.int32)
    pix_lab[inside] = lab[r[inside], c[inside]]

    # cropland fraction: count fine WorldCover samples per MODIS pixel
    crop = np.zeros(n * n)
    tot = np.zeros(n * n)
    for wlon, wlat, a in _worldcover_crop():
        LO, LA = np.meshgrid(wlon, wlat)
        rr, cc = _lonlat_to_pixel(LO.ravel(), LA.ravel(), n)
        ok = (rr >= 0) & (rr < n) & (cc >= 0) & (cc < n) & (a.ravel() > 0)
        flat = rr[ok] * n + cc[ok]
        tot += np.bincount(flat, minlength=n * n)
        crop += np.bincount(flat, weights=(a.ravel()[ok] == 40).astype(float), minlength=n * n)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(tot > 0, crop / tot, np.nan)

    flat_lab = pix_lab.ravel()
    order = np.argsort(flat_lab, kind="stable")
    starts = np.concatenate([[0], np.cumsum(np.bincount(flat_lab, minlength=max(names) + 1))])
    cover = coverage(WC_EXTENT)
    all_g: dict[str, list] = {}
    crop_g: dict[str, list] = {}
    is_crop = np.nan_to_num(frac) >= CROP_FRAC
    for i, uid in names.items():
        idx = order[starts[i]:starts[i + 1]]
        county = uid.split("-")[0]
        all_g.setdefault(uid, []).append(idx)
        all_g.setdefault(county, []).append(idx)
        if cover[uid] >= WC_MIN_COVER:
            crop_g.setdefault(uid, []).append(idx[is_crop[idx]])
        if cover[county] >= WC_MIN_COVER:
            crop_g.setdefault(county, []).append(idx[is_crop[idx]])
    all_u = {u: np.concatenate(v) for u, v in all_g.items()}
    crop_u = {u: np.concatenate(v) for u, v in crop_g.items()}
    crop_u = {u: v for u, v in crop_u.items() if v.size >= MIN_CROP_PX[n]}
    return frac, all_u, crop_u


def unit_means(a: np.ndarray, groups: dict[str, np.ndarray]) -> dict[str, float]:
    flat = a.ravel()
    out = {}
    for uid, idx in groups.items():
        if idx.size == 0:
            out[uid] = np.nan
            continue
        v = flat[idx]
        ok = v[~np.isnan(v)]
        out[uid] = float(ok.mean()) if ok.size >= MIN_CLEAR * idx.size and ok.size else np.nan
    return out


# ----------------------------------------------------------------------------- files
def _files(folder: str, prefix: str) -> list[tuple[date, object]]:
    out = {}
    for f in sorted(extra(folder).glob(f"{prefix}.A*.h{H:02d}v{V:02d}.*.hdf")):
        m = re.search(r"\.A(\d{4})(\d{3})\.", f.name)
        d = date(int(m.group(1)), 1, 1) + timedelta(days=int(m.group(2)) - 1)
        out[d] = f  # one granule per date (latest processing wins)
    return sorted(out.items())


def _read(f, layer: str) -> np.ndarray:
    sd = SD(str(f), SDC.READ)
    try:
        return sd.select(layer).get()
    finally:
        sd.end()


def _composite_days(start: date) -> list[date]:
    """8-day composite; the last one of a year stops at 31 Dec."""
    end = min(start + timedelta(days=7), date(start.year, 12, 31))
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _to_months(series: list[tuple[date, dict[str, float]]], how: str, keys: list[str]) -> dict[str, list]:
    """8-day unit values -> monthly. how='sum': value is a period total; 'mean': a state."""
    pos = {k: i for i, k in enumerate(keys)}
    units = {u for _, d in series for u in d}
    acc = {u: np.zeros(len(keys)) for u in units}
    days = {u: np.zeros(len(keys)) for u in units}
    for start, d in series:
        ds = _composite_days(start)
        for u, v in d.items():
            if np.isnan(v):
                continue
            per_day = v / len(ds) if how == "sum" else v
            for day in ds:
                k = pos.get(f"{day.year:04d}-{day.month:02d}")
                if k is not None:
                    acc[u][k] += per_day
                    days[u][k] += 1
    ndays = np.array([calendar.monthrange(int(k[:4]), int(k[5:]))[1] for k in keys])
    out = {}
    for u in units:
        with np.errstate(invalid="ignore", divide="ignore"):
            if how == "sum":
                v = np.where(days[u] >= ndays, acc[u], np.nan)
            else:
                v = np.where(days[u] >= 0.5 * ndays, acc[u] / days[u], np.nan)
        out[u] = v
    return out


def _month_range(dates: list[date]) -> list[str]:
    a, b = dates[0], dates[-1]
    n = (b.year - a.year) * 12 + b.month - a.month + 1
    return month_keys(a.year, a.month, n)


# ----------------------------------------------------------------------------- products
CROP_NOTE = (
    "Averaged over cropland pixels only (≥ 50 % ESA WorldCover 2021 'cropland' inside the pixel). "
    "Not available for Vâlcea county and the few communes outside the downloaded WorldCover tiles (south of 45 °N / west of 21 °E). "
)


def ndvi() -> None:
    files = _files("modis_ndvi", "MOD13A3")
    if not files:
        print("  no MOD13A3 files, skipping NDVI")
        return
    _, all_u, crop_u = pixel_groups(1200)
    keys = [f"{d.year:04d}-{d.month:02d}" for d, _ in files]
    per = {"crop": {u: [] for u in crop_u}, "all": {u: [] for u in all_u}}
    for _, f in files:
        a = _read(f, "1 km monthly NDVI").astype(float)
        rel = _read(f, "1 km monthly pixel reliability")
        a[(a < -2000) | (a > 10000) | (rel < 0) | (rel > 1)] = np.nan  # keep good (0) / marginal (1)
        a *= 1e-4
        for kind, groups in (("crop", crop_u), ("all", all_u)):
            m = unit_means(a, groups)
            for u in groups:
                per[kind][u].append(m[u])
    base = {
        "source": "NASA MODIS Terra MOD13A3.061 monthly vegetation indices, tile h19v04 (LP DAAC)",
        "variable": "1 km monthly NDVI",
        "unit": "NDVI",
        "aggregation": "mean",
        "period": {"start": keys[0], "end": keys[-1], "step": "month"},
        "resolution": "1 km",
        "status": "complete",
    }
    print(f"  NDVI: {len(keys)} months {keys[0]} – {keys[-1]}, cropland units {len(crop_u)}, all-land units {len(all_u)}")
    write_dataset("modis_ndvi", {**base, "label": "Vegetation index on cropland (NDVI)", "confidence": {
        "county": "high", "commune": "medium",
        "note": CROP_NOTE + "Good / marginal-quality pixels only; months with < 30 % clear pixels dropped. "
        "Mixes all crops: a greenness signal, not a yield estimate.",
    }}, keys, {u: values(v, 3) for u, v in per["crop"].items()})
    write_dataset("modis_ndvi_all", {**base, "label": "Vegetation index, all land (NDVI)", "confidence": {
        "county": "high", "commune": "medium",
        "note": "Mean over all land in the unit (forest, grassland, farmland), so in hilly / mountain units it mostly reflects forest. "
        "Good / marginal-quality pixels only; months with < 30 % clear pixels dropped.",
    }}, keys, {u: values(v, 3) for u, v in per["all"].items()})


def et() -> None:
    files = _files("modis_et", "MOD16A2GF")
    if not files:
        print("  no MOD16A2GF files, skipping ET")
        return
    _, _, crop_u = pixel_groups(2400)
    series = {"ET_500m": [], "PET_500m": []}
    for d, f in files:
        for layer in series:
            a = _read(f, layer).astype(float)
            a[(a < 0) | (a > 32700)] = np.nan  # 32761–32767 = fill / water / urban / barren
            series[layer].append((d, unit_means(a * 0.1, crop_u)))
    keys = _month_range([d for d, _ in files])
    base = {
        "source": "NASA MODIS Terra MOD16A2GF.061 gap-filled 8-day evapotranspiration, tile h19v04 (LP DAAC)",
        "unit": "mm",
        "aggregation": "sum",
        "resolution": "500 m",
        "status": "complete",
        "confidence": {
            "county": "high", "commune": "medium",
            "note": CROP_NOTE + "Satellite-driven model (Penman–Monteith with MODIS vegetation); 8-day totals spread over the calendar days they cover.",
        },
    }
    for layer, name, label in (("ET_500m", "modis_et", "Evapotranspiration on cropland (satellite)"),
                               ("PET_500m", "modis_pet", "Potential evapotranspiration on cropland (satellite)")):
        m = _to_months(series[layer], "sum", keys)
        ok = [i for i in range(len(keys)) if any(np.isfinite(v[i]) for v in m.values())]
        k2 = keys[ok[0]: ok[-1] + 1]
        print(f"  {name}: {k2[0]} – {k2[-1]}, {len(m)} units")
        write_dataset(name, {**base, "label": label, "variable": layer,
                             "period": {"start": k2[0], "end": k2[-1], "step": "month"}},
                      k2, {u: values(v[ok[0]: ok[-1] + 1], 1) for u, v in m.items()})


def _lst_ok(qc: np.ndarray) -> np.ndarray:
    """MOD11A2 QC: bits 0–1 = 00 (good) or 01 (other) with LST error bits 6–7 ≤ 01 (≤ 2 K)."""
    mand = qc & 0b11
    err = (qc >> 6) & 0b11
    return (mand == 0) | ((mand == 1) & (err <= 1))


def lst() -> None:
    files = _files("modis_lst", "MOD11A2")
    if not files:
        print("  no MOD11A2 files, skipping LST")
        return
    _, _, crop_u = pixel_groups(1200)
    series = {"Day": [], "Night": []}
    for d, f in files:
        for part in series:
            a = _read(f, f"LST_{part}_1km").astype(float)
            qc = _read(f, f"QC_{part}").astype(np.int64)
            a[(a == 0) | ~_lst_ok(qc)] = np.nan
            series[part].append((d, unit_means(a * 0.02 - 273.15, crop_u)))
    keys = _month_range([d for d, _ in files])
    base = {
        "source": "NASA MODIS Terra MOD11A2.061 8-day land surface temperature, tile h19v04 (LP DAAC)",
        "unit": "°C",
        "aggregation": "mean",
        "period": {"start": keys[0], "end": keys[-1], "step": "month"},
        "resolution": "1 km",
        "status": "complete",
        "confidence": {
            "county": "high", "commune": "medium",
            "note": CROP_NOTE + "Clear-sky only (cloudy days are missing, so cloudy months are biased warm by day). "
            "Surface (skin) temperature at the ~10:30 / ~22:30 Terra overpass, not air temperature; one 8-day composite (2022-10-16) is missing.",
        },
    }
    for part, name, label in (("Day", "modis_lst_day", "Daytime land surface temperature on cropland"),
                              ("Night", "modis_lst_night", "Night-time land surface temperature on cropland")):
        m = _to_months(series[part], "mean", keys)
        print(f"  {name}: {keys[0]} – {keys[-1]}, {len(m)} units")
        write_dataset(name, {**base, "label": label, "variable": f"LST_{part}_1km"}, keys,
                      {u: values(v, 1) for u, v in m.items()})


def main() -> None:
    load_units()
    frac, _, crop_u = pixel_groups(1200)
    print(f"  cropland pixels (1 km, ≥ {CROP_FRAC:.0%} WorldCover cropland): {int((np.nan_to_num(frac) >= CROP_FRAC).sum()):,}; "
          f"units with cropland series: {len(crop_u)}")
    ndvi()
    et()
    lst()


if __name__ == "__main__":
    main()
