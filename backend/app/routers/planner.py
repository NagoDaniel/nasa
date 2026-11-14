"""'Plan my field': saved answers per field, the plan, and harvest reports the models learn from."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from .. import datasets as ds
from ..assistant.guard import RateLimiter, client_key
from ..db import get_session
from ..models import FieldPlan, Field_, HarvestReport
from ..planner import climate as C
from ..planner import learning as L
from ..planner.plan import CROPS, build_plan
from ..planner.yields import expected_county
from ..scoring.forecast import forecast

router = APIRouter(prefix="/planner", tags=["planner"])
writes = RateLimiter(30, 400, 0)
Crop = Literal["maize", "wheat", "barley", "oats", "pea", "chickpea", "sunflower", "soy", "flax"]
PROBLEMS = Literal["drought", "hail", "frost", "pests", "disease", "mycotoxins", "waterlogging", "lodging", "other"]


class PastSeason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=2000, le=2100)
    crop: Crop
    yield_t_ha: float | None = Field(None, ge=0, le=25)


class SoilTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ph: float | None = Field(None, ge=3, le=10)
    soc_g_kg: float | None = Field(None, ge=0, le=200)
    texture: str | None = Field(None, max_length=30)


class Answers(BaseModel):
    """The planner questions (see the frontend wizard for wording)."""
    model_config = ConfigDict(extra="forbid")
    history: list[PastSeason] = Field(default_factory=list, max_length=5)
    consider: list[Crop] = Field(default_factory=lambda: list(CROPS))
    avoid: list[Crop] = Field(default_factory=list)
    must_grow: Crop | None = None
    must_min: int = Field(1, ge=1, le=2)
    irrigation: Literal["yes", "partly", "no"] = "no"
    planter: bool = True
    combine: bool = True
    n_limit: float | None = Field(None, ge=0, le=300)
    contract_crop: Crop | None = None
    priorities: dict[Literal["yield", "water", "soil", "risk"], float] = Field(
        default_factory=lambda: {"yield": 25, "water": 25, "soil": 25, "risk": 25})
    risk: Literal["careful", "balanced", "bold"] = "balanced"
    maturity: dict[Literal["maize", "sunflower", "soy"], Literal["suggest", "early", "medium", "late"]] = Field(default_factory=dict)
    prices: dict[Crop, float] = Field(default_factory=dict)
    costs: dict[Crop, float] = Field(default_factory=dict)
    soil_test: SoilTest = Field(default_factory=SoilTest)
    problems: list[PROBLEMS] = Field(default_factory=list)
    years: Literal[3, 4] = 4


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=2000, le=2100)
    crop: Crop
    yield_t_ha: float | None = Field(None, ge=0, le=25)
    maturity: Literal["early", "medium", "late"] | None = None
    irrigated: bool = False
    problems: list[PROBLEMS] = Field(default_factory=list)


def _limit(request: Request) -> None:
    ok, retry = writes.hit(client_key(request.client.host if request.client else None, request.headers.get("x-forwarded-for")))
    if not ok:
        raise HTTPException(429, "Too many changes, please wait a moment", headers={"Retry-After": str(retry)})


def _field(s: Session, fid: int) -> tuple[Field_, dict]:
    f = s.get(Field_, fid)
    if f is None:
        raise HTTPException(404, "Field not found")
    if not f.commune_id:
        raise HTTPException(422, "This field is outside the study area (Alba and neighbouring counties)")
    unit = ds.require_unit(f.commune_id)
    return f, {"id": f.id, "name": f.name, "area_ha": f.area_ha, "commune_id": f.commune_id,
               "commune": unit["name"], "county": unit["county"]}


def _answers(s: Session, fid: int) -> FieldPlan | None:
    return s.exec(select(FieldPlan).where(FieldPlan.field_id == fid)).first()


def _report_dict(r: HarvestReport, county: str) -> dict:
    return {"id": r.id, "field_id": r.field_id, "year": r.year, "crop": r.crop, "yield_t_ha": r.yield_t_ha,
            "maturity": r.maturity, "irrigated": r.irrigated, "problems": json.loads(r.problems_json), "source": r.source,
            "county": county}


def _all_reports(s: Session) -> list[dict]:
    units = ds.units_index()
    out = []
    for r, f in s.exec(select(HarvestReport, Field_).where(HarvestReport.field_id == Field_.id)):
        u = units.get(f.commune_id or "")
        if u:
            out.append(_report_dict(r, u["county"]))
    return out


def _expected():
    inputs, ins = ds.store.get("derived/forecast_inputs.json"), ds.ins()
    return lambda crop, county, year: expected_county(crop, county, year, inputs, ins)


def _learning(s: Session, fid: int) -> dict[str, Any]:
    exp = _expected()
    allr = _all_reports(s)
    mine = [r for r in allr if r["field_id"] == fid]
    return {"field": L.field_level(mine, exp), "shared": L.shared_effects(allr, exp, ds.traits()),
            "problems": L.problems_summary(mine)}


def _start_year() -> int:
    t = date.today()
    return t.year + 1 if t.month >= 8 else t.year


@router.get("/fields/{fid}")
def get_field(fid: int, s: Session = Depends(get_session)) -> dict[str, Any]:
    _, info = _field(s, fid)
    fp = _answers(s, fid)
    reps = [r for r in _all_reports(s) if r["field_id"] == fid]
    return {"field": info, "answers": json.loads(fp.answers_json) if fp else None, "reports": reps,
            "learning": _learning(s, fid), "start_year": _start_year()}


def _save_answers(s: Session, fid: int, a: Answers) -> None:
    fp = _answers(s, fid) or FieldPlan(field_id=fid)
    fp.answers_json = a.model_dump_json()
    fp.updated_at = datetime.now(timezone.utc)
    s.add(fp)
    # past seasons entered in the planner count as reports (source "history"); after-harvest reports win
    for old in s.exec(select(HarvestReport).where(HarvestReport.field_id == fid, HarvestReport.source == "history")):
        s.delete(old)
    reported = {r.year for r in s.exec(select(HarvestReport).where(HarvestReport.field_id == fid, HarvestReport.source == "report"))}
    for h in a.history:
        if h.year not in reported:
            s.add(HarvestReport(field_id=fid, year=h.year, crop=h.crop, yield_t_ha=h.yield_t_ha,
                                irrigated=a.irrigation == "yes", problems_json=json.dumps(a.problems), source="history"))
    s.commit()


@router.put("/fields/{fid}/answers")
def put_answers(fid: int, a: Answers, request: Request, s: Session = Depends(get_session)) -> dict:
    _limit(request)
    _field(s, fid)
    _save_answers(s, fid, a)
    return {"saved": True}


@router.post("/fields/{fid}/plan")
def make_plan(fid: int, a: Answers, request: Request, s: Session = Depends(get_session)) -> dict[str, Any]:
    _limit(request)
    f, info = _field(s, fid)
    _save_answers(s, fid, a)
    learn = _learning(s, fid)
    unit = ds.require_unit(f.commune_id)
    ag = ds.agro(f.commune_id)
    d = {"traits": ds.traits(), "inputs": ds.store.get("derived/forecast_inputs.json"), "ins": ds.ins(),
         "prices": ds.store.get("crops/prices.json"), "unit": unit, "agro": {"years": ag["years"], "values": ag["values"]},
         "soil": ds.soil(f.commune_id)["values"], "terrain": (ds.terrain(f.commune_id) or {}).get("values")}
    am = a.model_dump()
    am["history"] = [h for h in am["history"]]
    start = _start_year()
    plan = build_plan(info, am, d, learn["field"], learn["shared"], start, autumn_open=date.today() <= date(start - 1, 10, 20))
    # this season (latest weather year) for what the farmer grew in it
    season = None
    inputs = d["inputs"]
    last = inputs["years"][-1]
    grown = next((h for h in a.history if h.year == last), None)
    if grown:
        counties = {u["id"]: u["name"] for u in ds.units_index().values() if u["kind"] == "county"}
        fc = forecast(grown.crop, counties, d["ins"], inputs, d["traits"])
        cf = fc["counties"].get(info["county"], {}).get("forecast")
        season = {
            "year": last, "crop": grown.crop, "your_yield_t_ha": grown.yield_t_ha,
            "county_forecast": None if not cf else {"t_ha": cf["yield_kg_ha"] / 1000, "range_80_t_ha": [v / 1000 for v in cf["intervals_kg_ha"]["80"]],
                                                    "signal": cf["model"]["signal"]},
            "quality": C.season_check(grown.crop, d["traits"]["crops"][grown.crop], inputs["counties"][info["county"]], inputs["years"], last),
        }
    return {"field": info, "plan": plan, "learning": learn, "season": season,
            "method": [
                "Sowing, maturity and harvest timing: NASA POWER daily weather 2000–2026 for the county (frost dates, 7-day mean temperature, heat sums above 10 °C).",
                "Yield: county trend from INS yields 2000–2025 (ranges = how far real years fell from the trend), × your field's own level learned from your reports, × previous-crop effect.",
                "Rotation choice: the dashboard's rotation score (yield, water, soil, risk) with your weights; every allowed sequence is checked.",
                "Rotation effects (after legume, repeated crop) start from literature values and move toward what farmers report as reports accumulate.",
                "Seed rates, maturity heat sums and sowing temperatures are approximate agronomy values; confirm with your seed supplier.",
            ]}


@router.post("/fields/{fid}/reports")
def add_report(fid: int, body: ReportIn, request: Request, s: Session = Depends(get_session)) -> dict[str, Any]:
    _limit(request)
    _field(s, fid)
    for old in s.exec(select(HarvestReport).where(HarvestReport.field_id == fid, HarvestReport.year == body.year)):
        s.delete(old)  # one season per field and year; the new report replaces history / older report
    s.add(HarvestReport(field_id=fid, year=body.year, crop=body.crop, yield_t_ha=body.yield_t_ha, maturity=body.maturity,
                        irrigated=body.irrigated, problems_json=json.dumps(body.problems), source="report"))
    s.commit()
    return {"saved": True, "learning": _learning(s, fid)}


@router.delete("/reports/{rid}")
def delete_report(rid: int, request: Request, s: Session = Depends(get_session)) -> dict:
    _limit(request)
    r = s.get(HarvestReport, rid)
    if r is None:
        raise HTTPException(404, "Report not found")
    s.delete(r)
    s.commit()
    return {"deleted": rid}


@router.get("/learning")
def learning(s: Session = Depends(get_session)) -> dict[str, Any]:
    """What the shared models have learned from all reports so far."""
    allr = _all_reports(s)
    return {"shared": L.shared_effects(allr, _expected(), ds.traits()), "problems": L.problems_summary(allr),
            "n_reports": len(allr), "n_fields": len({r["field_id"] for r in allr})}
