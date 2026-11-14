from typing import Any

from fastapi import APIRouter

from .. import datasets as ds
from ..i18n import cropclass, landcover, localize, ro, texture
from ..maplayers import map_layer

router = APIRouter(tags=["area"])


@router.get("/units")
def units() -> list[dict]:
    """Analysis units: the 8 study-area counties and their communes."""
    return list(ds.units_index().values())


@router.get("/area/{uid}")
def area(uid: str) -> dict[str, Any]:
    """Everything the farmer dashboard needs for one county or commune."""
    unit = ds.require_unit(uid)
    county = unit["county"]
    indicators = [x for n in ds.indicator_names() if (x := ds.indicator(n, uid))]
    ins = ds.ins()
    out = {
        "unit": unit,
        "indicators": indicators,
        "agro_yearly": ds.agro(uid),
        "soil": ds.soil(uid),
        "terrain": ds.terrain(uid),
        "cropmap": ds.cropmap(uid),
        "crop_stats": {
            "source": ins["source"], "years": ins["years"], "confidence": ins["confidence"],
            "county": county, "values": ins["counties"].get(county, {}),
        },
    }
    if not ro():
        return out
    out = localize(out)
    soil_v = (out.get("soil") or {}).get("values")
    if soil_v and soil_v.get("texture"):
        soil_v["texture"] = texture(soil_v["texture"])
    if out.get("cropmap"):
        out["cropmap"]["classes"] = {k: cropclass(v) for k, v in out["cropmap"]["classes"].items()}
    if out.get("terrain") and out["terrain"].get("classes"):
        out["terrain"]["classes"] = {k: landcover(v) for k, v in out["terrain"]["classes"].items()}
    return out


@router.get("/map")
def map_values(kind: str, key: str) -> dict[str, Any]:
    """Values per unit (all years) for colouring the map: kind = indicator | agro | soil | cropshare."""
    return map_layer(kind, key)
