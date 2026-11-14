from typing import Any

from fastapi import APIRouter

from .. import datasets as ds

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
    return {
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
