"""Per-unit values for colouring the map by whatever the dashboard is showing.

One response holds every year, so scrubbing through years in the UI is instant
and colours stay comparable between years.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .json_store import store

BLUE = {"imerg_precip", "power_precip", "gldas_rain", "gldas_rootmoist", "gldas_soilmoist_0_10", "power_soil_wetness",
        "gldas_et", "gldas_pet", "power_rh", "power_frost_days", "rain_flowering_small_grain",
        "wet_days_flowering_small_grain", "rain_harvest_small_grain", "rain_harvest_summer_crops", "late_frost",
        "precip_apr_sep", "et_apr_sep", "rootmoist_jja"}
GREEN = {"modis_ndvi"}
DIVERGING = {"rootmoist_jja_z", "water_balance_apr_sep"}


def _palette(key: str) -> str:
    if key in DIVERGING:
        return "div"
    if key in GREEN:
        return "green"
    return "blue" if key in BLUE else "red"


def _indicator(key: str) -> dict[str, Any]:
    try:
        d = store.get(f"nasa/{key}.json")
    except FileNotFoundError:
        raise HTTPException(404, f"Unknown indicator '{key}'")
    keys: list[str] = d["keys"]
    by_year: dict[str, list[int]] = {}
    for i, k in enumerate(keys):
        by_year.setdefault(k[:4], []).append(i)
    monthly = d["period"]["step"] == "month"
    need = 12 if monthly else 20  # only complete years, so totals are comparable
    years = sorted(y for y, idx in by_year.items() if len(idx) >= need)
    is_sum = d.get("aggregation") == "sum"
    values = {}
    for uid, arr in d["units"].items():
        out = []
        for y in years:
            vs = [arr[i] for i in by_year[y] if arr[i] is not None]
            if len(vs) < need:
                out.append(None)
            else:
                out.append(round(sum(vs) if is_sum else sum(vs) / len(vs), 2))
        values[uid] = out
    return {"label": d["label"], "unit": f"{d['unit']}/yr" if is_sum else d["unit"], "years": years, "values": values,
            "palette": _palette(key), "source": d["source"]}


def _agro(key: str) -> dict[str, Any]:
    d = store.get("derived/agro_yearly.json")
    meta = d["indicators"].get(key)
    if meta is None:
        raise HTTPException(404, f"Unknown season indicator '{key}'")
    return {"label": meta["label"], "unit": meta["unit"], "years": [str(y) for y in d["years"]],
            "values": {u: rec.get(key, []) for u, rec in d["units"].items()}, "palette": _palette(key),
            "source": meta["source"]}


def _soil(key: str) -> dict[str, Any]:
    d = store.get("soil/soilgrids.json")
    meta = d["properties"].get(key)
    if meta is None:
        raise HTTPException(404, f"Unknown soil property '{key}'")
    return {"label": f"{meta['label']} (0–30 cm)", "unit": "" if meta["unit"] == "pH" else meta["unit"], "years": None,
            "values": {u: [(rec.get(key) or {}).get("median")] for u, rec in d["units"].items()},
            "palette": "brown", "source": d["source"]}


def _cropshare(key: str) -> dict[str, Any]:
    d = store.get("crops/cropmap.json")
    if key not in d["classes"]:
        raise HTTPException(404, f"Unknown crop class '{key}'")
    years = d["years"]
    values = {}
    for u, rec in d["units"].items():
        out = []
        for y in years:
            classes = rec.get(y) or {}
            arable = sum(n for c, n in classes.items() if 200 <= int(c) < 300)
            out.append(round(100 * classes.get(key, 0) / arable, 1) if arable >= 50 else None)
        values[u] = out
    return {"label": f"{d['classes'][key].capitalize()}: share of arable land", "unit": "%", "years": years,
            "values": values, "palette": "green", "source": d["source"]}


KINDS = {"indicator": _indicator, "agro": _agro, "soil": _soil, "cropshare": _cropshare}


def map_layer(kind: str, key: str) -> dict[str, Any]:
    fn = KINDS.get(kind)
    if fn is None:
        raise HTTPException(404, f"Unknown layer kind '{kind}'")
    return {"kind": kind, "key": key, **fn(key)}
