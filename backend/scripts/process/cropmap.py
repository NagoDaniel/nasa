"""JRC EUCROPMAP 2018 / 2022 (10 m, EPSG:3035) -> hectares per crop class per unit.

Read decimated to 100 m (nearest), so one pixel = 1 ha; unbiased for area shares
at county / commune scale, not for single fields.
"""

from __future__ import annotations

import numpy as np
import rasterio
from affine import Affine

from common import raw, write_json
from zonal import label_raster, unit_pixel_groups

CLASSES = {
    100: "artificial", 211: "common wheat", 212: "durum wheat", 213: "barley", 214: "rye", 215: "oats",
    216: "maize", 217: "rice", 218: "triticale", 219: "other cereals", 221: "potatoes", 222: "sugar beet",
    223: "other root crops", 230: "other industrial crops", 231: "sunflower", 232: "rapeseed", 233: "soya",
    240: "dry pulses", 250: "fodder crops", 290: "bare arable land", 300: "woodland / shrubland",
    500: "grassland", 600: "bare land", 700: "water", 800: "wetlands",
}
TO_CROP = {211: "wheat", 213: "barley", 215: "oats", 216: "maize", 231: "sunflower", 233: "soy", 240: "pulses", 232: "rapeseed"}
FACTOR = 10  # 10 m -> 100 m


def year_stats(path) -> dict[str, dict[str, int]]:
    with rasterio.open(path) as src:
        h, w = src.height // FACTOR, src.width // FACTOR
        arr = src.read(1, out_shape=(h, w)).astype(np.int32)
        transform = src.transform * Affine.scale(src.width / w, src.height / h)
        crs = src.crs
    labels, names = label_raster(transform, (h, w), crs)
    groups = unit_pixel_groups(labels, names)
    flat = arr.ravel()
    out = {}
    for uid, idx in groups.items():
        vals = flat[idx]
        codes, counts = np.unique(vals[vals > 0], return_counts=True)
        out[uid] = {str(int(c)): int(n) for c, n in zip(codes, counts)}
    return out


def main() -> None:
    years = {}
    for y in (2018, 2022):
        p = raw(f"crops/eucropmap/EUCROPMAP_{y}_AOI.tif")
        if p.exists():
            print(f"  reading {p.name} (decimated to 100 m)…")
            years[y] = year_stats(p)
    units = {}
    for y, per in years.items():
        for uid, rec in per.items():
            units.setdefault(uid, {})[str(y)] = rec
    ab = units.get("AB", {}).get("2022", {})
    print(f"  check: Alba 2022 maize {ab.get('216', 0):,} ha, wheat {ab.get('211', 0):,} ha, arable classes total "
          f"{sum(v for k, v in ab.items() if 200 <= int(k) < 300):,} ha")
    write_json(
        "crops/cropmap.json",
        {
            "source": "JRC EUCROPMAP 2018 and 2022 (CC BY 4.0, © European Union)",
            "resolution": "10 m map, counted at 100 m (1 pixel = 1 ha)",
            "unit": "ha",
            "classes": {str(k): v for k, v in CLASSES.items()},
            "crop_codes": {str(k): v for k, v in TO_CROP.items()},
            "years": sorted(str(y) for y in years),
            "confidence": {
                "county": "medium",
                "commune": "medium",
                "note": "Satellite classification (Sentinel-1); individual fields can be misclassified, totals are indicative. Two snapshots only, not a yearly series.",
            },
            "units": units,
        },
    )


if __name__ == "__main__":
    main()
