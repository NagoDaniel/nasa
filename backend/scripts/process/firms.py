"""NASA FIRMS VIIRS S-NPP active fires -> monthly vegetation-fire detections per unit."""

from __future__ import annotations

import numpy as np
import pandas as pd
from shapely import points
from shapely.strtree import STRtree

from common import YEARS, load_units, month_keys, raw, values, write_dataset


def main() -> None:
    frames = []
    for y in YEARS:
        f = raw(f"firms/romania_country_yearly/viirs-snpp_{y}_Romania.csv")
        if f.exists():
            frames.append(pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "confidence", "type"]))
    df = pd.concat(frames)
    # type 0 = presumed vegetation fire; drop low-confidence detections
    df = df[(df["type"] == 0) & (df["confidence"].isin(["n", "h"]))]
    df["ym"] = df["acq_date"].str[:7]
    units = load_units()
    tree = STRtree([u.geom for u in units])
    pts = points(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    pairs = tree.query(pts, predicate="within")  # (point idx, unit idx)
    keys = month_keys(YEARS[0], 1, 12 * len(YEARS))
    kidx = {k: i for i, k in enumerate(keys)}
    counts = {u.id: np.zeros(len(keys)) for u in units}
    ym = df["ym"].to_numpy()
    for p, ui in zip(*pairs):
        counts[units[ui].id][kidx[ym[p]]] += 1
    print(f"  {len(df)} vegetation-fire detections in Romania, {pairs.shape[1]} unit hits")
    write_dataset(
        "firms_fires",
        {
            "label": "Vegetation fire detections",
            "source": "NASA FIRMS, VIIRS S-NPP 375 m active fires (type 0, nominal/high confidence)",
            "variable": "fire detections",
            "unit": "detections",
            "aggregation": "sum",
            "period": {"start": keys[0], "end": keys[-1], "step": "month"},
            "resolution": "375 m points",
            "confidence": {
                "county": "medium",
                "commune": "medium",
                "note": "Includes agricultural stubble burning but also other vegetation fires; small or short fires and fires under cloud are missed. Not yet restricted to cropland.",
            },
            "status": "complete",
        },
        keys,
        {u: values(v, 0) for u, v in counts.items()},
    )


if __name__ == "__main__":
    main()
