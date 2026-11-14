"""Inputs for the season yield forecast (app/scoring/forecast.py): one table per county, 2000–2026.

Longer than agro_yearly (2015–2026) so the model trains on 26 seasons instead of 11.
Only NASA POWER is used (it covers 1981 onward; GLDAS raw is only 2015+ here), so every
year is computed the same way:
  - the crop-window indicators of agro_yearly (heat, frost, rain, dry spells, GDD), and
  - root-zone soil wetness (POWER GWETROOT) Jun–Jul and Jun–Aug, as anomalies (z-score
    vs 2000–2025), the stand-in for GLDAS soil moisture.
Yields: INS TEMPO AGR110A from 2000 (county average yield, kg/ha).
Output: data/derived/forecast_inputs.json (counties only).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agro_yearly import INDICATORS, POWER_SRC, _window, power_part
from common import AOI, aggregate, raw, values, write_json
from ins import COUNTY, CROPS
from power import MIN_VALID, load_power_grid, power_weights

YEARS = list(range(2000, 2027))
BASE = (2000, 2025)


def soil_wetness() -> dict[str, dict[str, np.ndarray]]:
    dates, _, _, a = load_power_grid()
    g = a["GWETROOT"]
    out = {}
    for key, (m0, m1) in {"gwetroot_jj_z": ((6, 1), (7, 31)), "gwetroot_jja_z": ((6, 1), (8, 31))}.items():
        arr = np.full((len(YEARS),) + g.shape[1:], np.nan)
        for i, y in enumerate(YEARS):
            w = _window(dates, y, m0, m1)
            if not w.any():
                continue
            sel = g[w]
            ok = (~np.isnan(sel)).sum(0) >= 0.95 * w.sum()
            with np.errstate(invalid="ignore"):
                arr[i] = np.where(ok, np.nanmean(sel, 0), np.nan)
        per = aggregate(arr, power_weights(), min_valid=MIN_VALID)
        base = np.array([BASE[0] <= y <= BASE[1] for y in YEARS])
        z = {}
        for u, v in per.items():
            with np.errstate(invalid="ignore", divide="ignore"):
                z[u] = (v - np.nanmean(v[base])) / np.nanstd(v[base])
        out[key] = z
    return out


def yields() -> dict[str, dict[str, list]]:
    f = raw("crops/ins_tempo/AGR110A_AOI_2000plus.csv")
    df = pd.read_csv(f, sep=", ", engine="python")
    df.columns = ["crop", "ownership", "area", "year", "um", "value"]
    for c in ["crop", "ownership", "area", "year"]:
        df[c] = df[c].astype(str).str.strip()
    df = df[df["ownership"] == "Total"]
    df["year"] = df["year"].str.replace("Anul ", "", regex=False).astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    out: dict = {}
    for crop, name in CROPS.items():
        sub = df[df["crop"] == name]
        for area, code in COUNTY.items():
            s = sub[sub["area"] == area].set_index("year")["value"]
            vals = [None if y not in s.index or pd.isna(s[y]) else float(s[y]) for y in YEARS]
            if any(vals):
                out.setdefault(code, {})[crop] = vals
    return out


def main() -> None:
    parts = {**power_part(YEARS), **soil_wetness()}
    keys = [k for k in INDICATORS if INDICATORS[k][2] == POWER_SRC] + ["gwetroot_jj_z", "gwetroot_jja_z"]
    meta = {k: {"label": INDICATORS[k][0], "unit": INDICATORS[k][1], "window": INDICATORS[k][3]} for k in keys if k in INDICATORS}
    meta["gwetroot_jj_z"] = {"label": "Root-zone soil wetness anomaly, Jun–Jul", "unit": "z-score", "window": "Jun–Jul"}
    meta["gwetroot_jja_z"] = {"label": "Root-zone soil wetness anomaly, Jun–Aug", "unit": "z-score", "window": "Jun–Aug"}
    counties = {c: {k: values(parts[k][c], 2) for k in keys} for c in AOI}
    y = yields()
    n26 = sum(1 for c in AOI if counties[c]["heat35_jul_aug"][-1] is not None)
    print(f"  {YEARS[0]}–{YEARS[-1]}: {len(keys)} indicators; counties with {YEARS[-1]} weather: {n26}/8; "
          f"yield series: {sum(len(v) for v in y.values())}")
    write_json("derived/forecast_inputs.json", {
        "years": YEARS,
        "indicators": meta,
        "sources": {
            "weather": "NASA POWER daily (MERRA-2), 0.5° × 0.625° grid, area-weighted to counties",
            "yields": "INS TEMPO AGR110A average yield per county (kg/ha), from 2000",
        },
        "counties": counties,
        "yields": y,
    })


if __name__ == "__main__":
    main()
