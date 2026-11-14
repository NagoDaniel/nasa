from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import datasets as ds
from ..i18n import localize
from ..scoring.forecast import forecast
from ..scoring.procurement import procurement
from ..scoring.rotation import score_rotation

router = APIRouter(tags=["crops"])


@router.get("/crops/traits")
def traits() -> dict[str, Any]:
    return ds.traits()


@router.get("/crops/stats")
def stats(county: str | None = None) -> dict[str, Any]:
    d = ds.ins()
    if county is None:
        return localize(d)
    if county not in d["counties"]:
        raise HTTPException(404, f"No statistics for '{county}'")
    return localize({k: v for k, v in d.items() if k != "counties"} | {"county": county, "values": d["counties"][county]})


class Priorities(BaseModel):
    yield_: float = Field(25, alias="yield", ge=0)
    water: float = Field(25, ge=0)
    soil: float = Field(25, ge=0)
    risk: float = Field(25, ge=0)

    def as_dict(self) -> dict[str, float]:
        return {"yield": self.yield_, "water": self.water, "soil": self.soil, "risk": self.risk}


class Rotation(BaseModel):
    name: str = ""
    crops: list[str] = Field(min_length=3, max_length=4)


class ScoreRequest(BaseModel):
    unit: str
    priorities: Priorities = Priorities()
    rotations: list[Rotation] = Field(min_length=1, max_length=3)


@router.post("/rotations/score")
def score(req: ScoreRequest) -> dict[str, Any]:
    ctx = ds.rotation_context(req.unit)
    unit = ctx.unit
    try:
        results = [{"name": r.name, **score_rotation(ctx, r.crops, req.priorities.as_dict())} for r in req.rotations]
    except ValueError as e:
        raise HTTPException(422, str(e))
    return localize({"unit": unit, "priorities": req.priorities.as_dict(), "results": results})


@router.get("/procurement")
def procurement_view(crop: str) -> dict[str, Any]:
    traits = ds.traits()
    if crop not in traits["crops"]:
        raise HTTPException(404, f"Unknown crop '{crop}'")
    counties, agro_all, fires, ndvi = ds.procurement_inputs()
    outlook = forecast(crop, counties, ds.ins(), ds.store.get("derived/forecast_inputs.json"), traits)
    return localize(procurement(crop, counties, ds.ins(), agro_all, traits, fires, ndvi, outlook))


@router.get("/forecast")
def forecast_view(crop: str) -> dict[str, Any]:
    """Season yield outlook per county for one crop (ridge regression on weather, tested leave-one-year-out)."""
    traits = ds.traits()
    if crop not in traits["crops"]:
        raise HTTPException(404, f"Unknown crop '{crop}'")
    counties = {u["id"]: u["name"] for u in ds.units_index().values() if u["kind"] == "county"}
    return localize(forecast(crop, counties, ds.ins(), ds.store.get("derived/forecast_inputs.json"), traits))
