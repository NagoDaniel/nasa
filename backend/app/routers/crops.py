from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import datasets as ds
from ..scoring.forecast import forecast
from ..scoring.procurement import procurement
from ..scoring.rotation import Context, score_rotation

router = APIRouter(tags=["crops"])


@router.get("/crops/traits")
def traits() -> dict[str, Any]:
    return ds.traits()


@router.get("/crops/stats")
def stats(county: str | None = None) -> dict[str, Any]:
    d = ds.ins()
    if county is None:
        return d
    if county not in d["counties"]:
        raise HTTPException(404, f"No statistics for '{county}'")
    return {k: v for k, v in d.items() if k != "counties"} | {"county": county, "values": d["counties"][county]}


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
    unit = ds.require_unit(req.unit)
    ins = ds.ins()
    agro = ds.agro(req.unit)
    ctx = Context(
        unit=unit,
        agro={"years": agro["years"], "values": agro["values"]},
        soil=ds.soil(req.unit)["values"],
        terrain=(ds.terrain(req.unit) or {}).get("values"),
        ins_county=ins["counties"].get(unit["county"], {}),
        ins_ro=ins["counties"].get("RO", {}),
        traits=ds.traits(),
    )
    try:
        results = [{"name": r.name, **score_rotation(ctx, r.crops, req.priorities.as_dict())} for r in req.rotations]
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"unit": unit, "priorities": req.priorities.as_dict(), "results": results}


@router.get("/procurement")
def procurement_view(crop: str) -> dict[str, Any]:
    traits = ds.traits()
    if crop not in traits["crops"]:
        raise HTTPException(404, f"Unknown crop '{crop}'")
    counties = {u["id"]: u["name"] for u in ds.units_index().values() if u["kind"] == "county"}
    agro_all = ds.store.get("derived/agro_yearly.json")
    fires = ds.store.get("nasa/firms_fires.json")["units"]
    try:
        nd = ds.store.get("nasa/modis_ndvi.json")
        ndvi = {"keys": nd["keys"], "units": {c: nd["units"].get(c) for c in counties}}
    except FileNotFoundError:
        ndvi = None
    outlook = forecast(crop, counties, ds.ins(), ds.store.get("derived/forecast_inputs.json"), traits)
    return procurement(crop, counties, ds.ins(), agro_all, traits, {c: fires.get(c) for c in counties}, ndvi, outlook)


@router.get("/forecast")
def forecast_view(crop: str) -> dict[str, Any]:
    """Season yield outlook per county for one crop (ridge regression on weather, tested leave-one-year-out)."""
    traits = ds.traits()
    if crop not in traits["crops"]:
        raise HTTPException(404, f"Unknown crop '{crop}'")
    counties = {u["id"]: u["name"] for u in ds.units_index().values() if u["kind"] == "county"}
    return forecast(crop, counties, ds.ins(), ds.store.get("derived/forecast_inputs.json"), traits)
