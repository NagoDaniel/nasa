"""ISRIC SoilGrids 2.0 (250 m) -> topsoil (0–30 cm) properties per unit."""

from __future__ import annotations

import numpy as np
import rasterio

from common import raw, write_json
from zonal import label_raster, unit_pixel_groups

# prop: (label, divisor -> conventional unit, unit)
PROPS = {
    "soc": ("Soil organic carbon", 10, "g/kg"),
    "phh2o": ("pH (water)", 10, "pH"),
    "clay": ("Clay", 10, "%"),
    "sand": ("Sand", 10, "%"),
    "silt": ("Silt", 10, "%"),
    "nitrogen": ("Total nitrogen", 100, "g/kg"),
    "bdod": ("Bulk density", 100, "g/cm³"),
    "cec": ("Cation exchange capacity", 10, "cmol(c)/kg"),
}
DEPTHS = [("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)]


def usda_texture(clay: float, sand: float, silt: float) -> str:
    """USDA soil texture triangle (percentages)."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 1.5 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    if clay >= 40 and sand <= 45 and silt < 40:
        return "clay"
    return "loam"


def topsoil(prop: str):
    """Depth-weighted 0–30 cm mean in conventional units; NaN where any layer is nodata (0)."""
    acc, meta = None, None
    for depth, w in DEPTHS:
        with rasterio.open(raw(f"soil/soilgrids/{prop}_{depth}_mean.tif")) as src:
            a = src.read(1).astype(float)
            meta = (src.transform, src.shape)
        a[a == 0] = np.nan
        acc = a * w if acc is None else acc + a * w
    return acc / 30 / PROPS[prop][1], meta


def main() -> None:
    layers = {}
    meta = None
    for p in PROPS:
        layers[p], meta = topsoil(p)
    labels, names = label_raster(*meta)
    groups = unit_pixel_groups(labels, names)
    units = {}
    for uid, idx in groups.items():
        rec = {}
        for p, arr in layers.items():
            v = arr.ravel()[idx]
            v = v[~np.isnan(v)]
            if v.size == 0:
                rec[p] = None
                continue
            p10, p50, p90 = np.percentile(v, [10, 50, 90])
            nd = 2 if p in ("bdod", "nitrogen", "phh2o") else 1
            rec[p] = {"median": round(p50, nd), "p10": round(p10, nd), "p90": round(p90, nd)}
        valid = (~np.isnan(layers["soc"].ravel()[idx])).mean() if idx.size else 0
        rec["valid_share"] = round(float(valid), 3)
        rec["pixels"] = int(idx.size)
        if rec.get("clay") and rec.get("sand") and rec.get("silt"):
            rec["texture"] = usda_texture(rec["clay"]["median"], rec["sand"]["median"], rec["silt"]["median"])
        units[uid] = rec
    write_json(
        "soil/soilgrids.json",
        {
            "source": "ISRIC SoilGrids 2.0 (CC BY 4.0), predicted mean",
            "depth": "0–30 cm, depth-weighted (0–5, 5–15, 15–30 cm)",
            "resolution": "250 m",
            "properties": {p: {"label": l, "unit": u} for p, (l, _, u) in PROPS.items()},
            "statistic": "median and 10th–90th percentile of pixels in the unit (water/urban excluded)",
            "texture": "USDA texture class of the median clay/sand/silt",
            "confidence": {
                "county": "medium",
                "commune": "medium",
                "note": "Modelled soil map (machine learning on soil profiles), not field measurements. Good for comparing areas; a lab test is needed for a specific field.",
            },
            "units": units,
        },
    )


if __name__ == "__main__":
    main()
