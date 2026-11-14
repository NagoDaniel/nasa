"""Read-only access to the processed JSON data (in memory via json_store)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .json_store import store

__all__ = ["store"]

# Indicators shown on the farmer dashboard, in display order.
INDICATOR_ORDER = [
    "imerg_precip", "modis_ndvi", "smap_soil_moisture", "gldas_rootmoist", "power_heat_days", "modis_et",
    "modis_lst_day", "grace_tws", "power_tmax", "firms_fires",
    "gldas_et", "modis_pet", "modis_ndvi_all", "modis_lst_night", "power_precip", "gldas_soilmoist_0_10", "gldas_pet",
    "gldas_rain", "power_tmean", "power_frost_days", "power_gdd10", "power_rh", "power_soil_wetness",
]


def units_index() -> dict[str, dict]:
    return {u["id"]: u for u in store.get("units.json")["units"]}


def require_unit(uid: str) -> dict:
    u = units_index().get(uid)
    if u is None:
        raise HTTPException(404, f"'{uid}' is outside the study area (Alba + neighbouring counties)")
    return u


def indicator_names() -> list[str]:
    have = set(store.list("nasa"))
    return [n for n in INDICATOR_ORDER if n in have] + sorted(have - set(INDICATOR_ORDER))


def indicator(name: str, uid: str) -> dict | None:
    d = store.get(f"nasa/{name}.json")
    vals = d.get("units", {}).get(uid)
    if vals is None:
        return None
    meta = {k: v for k, v in d.items() if k not in ("units",)}
    return {"name": name, **meta, "values": vals}


def agro(uid: str) -> dict[str, Any]:
    from .scoring.hazards import HAZARDS

    d = store.get("derived/agro_yearly.json")
    return {"years": d["years"], "indicators": d["indicators"], "confidence": d["confidence"],
            "hazards": {k: {"op": h.op, "threshold": h.threshold, "text": h.text} for k, h in HAZARDS.items()},
            "values": d["units"].get(uid, {})}


def soil(uid: str) -> dict[str, Any]:
    d = store.get("soil/soilgrids.json")
    return {k: v for k, v in d.items() if k != "units"} | {"values": d["units"].get(uid)}


def terrain(uid: str) -> dict[str, Any] | None:
    """SRTM terrain + WorldCover land cover; None when the unit is outside the downloaded tiles."""
    try:
        d = store.get("land/terrain.json")
    except FileNotFoundError:
        return None
    vals = d["units"].get(uid)
    if vals is None:
        return None
    return {k: v for k, v in d.items() if k != "units"} | {"values": vals}


def ins() -> dict[str, Any]:
    return store.get("crops/ins_stats.json")


def traits() -> dict[str, Any]:
    return store.get("crops/crop_traits.json")


def cropmap(uid: str) -> dict[str, Any] | None:
    try:
        d = store.get("crops/cropmap.json")
    except FileNotFoundError:
        return None
    return {k: v for k, v in d.items() if k != "units"} | {"values": d["units"].get(uid)}
