"""Drawn fields: save / edit / delete, measure, surrounding-area context, field imagery."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, func, select

from ..assistant.guard import RateLimiter, client_key, sanitize
from ..config import settings
from ..db import get_session
from ..field import coarse, imagery
from ..field.geom import check_size, describe, parse
from ..models import Farm, FieldPlan, Field_, HarvestReport
from ..i18n import L, localize, num, ro, t

router = APIRouter(prefix="/fields", tags=["fields"])
jobs_limiter = RateLimiter(settings.rate_field_jobs_per_min, settings.rate_field_jobs_per_day, 0)
writes_limiter = RateLimiter(20, 300, 0)


class GeomIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geometry: dict[str, Any]


class FieldIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field("", max_length=60)
    geometry: dict[str, Any]


class FieldPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=60)
    geometry: dict[str, Any] | None = None


def _limit(lim: RateLimiter, request: Request) -> None:
    ok, retry = lim.hit(client_key(request.client.host if request.client else None, request.headers.get("x-forwarded-for")))
    if not ok:
        raise HTTPException(429, "Too many requests, please wait a moment", headers={"Retry-After": str(retry)})


def _out(f: Field_) -> dict:
    return {"id": f.id, "name": f.name, "area_ha": f.area_ha, "commune_id": f.commune_id,
            "geometry": json.loads(f.geometry_geojson)}


def _farm(s: Session) -> Farm:
    farm = s.exec(select(Farm).where(Farm.name == "Demo farm")).first()
    if farm is None:
        farm = Farm(name="Demo farm")
        s.add(farm)
        s.commit()
        s.refresh(farm)
    return farm


@router.post("/measure")
def measure(body: GeomIn) -> dict:
    """Area and location of a drawn outline (also used while drawing)."""
    poly = parse(body.geometry)
    d = describe(poly)
    ha = d["area_ha"]
    d["warnings"] = []
    if ha < 1:
        d["warnings"].append(t("fd_under1"))
    if d["commune"] is None:
        d["warnings"].append(t("fd_outside"))
    d["limits"] = {"min_ha": 0.5, "max_ha": 5000}
    return localize(d)


@router.post("/context")
def context(body: GeomIn) -> dict:
    """Coarse datasets for the field: native grid cells (surrounding-area estimates) and soil pixels."""
    poly = parse(body.geometry)
    check_size(poly)
    d = describe(poly)
    return localize({"field": d, **coarse.context(poly, (d["commune"] or {}).get("id"))})


@router.post("/vegetation")
def vegetation(body: GeomIn, request: Request) -> dict:
    """Start (or reuse) the imagery job for a field; poll GET /fields/vegetation/{job_id}."""
    poly = parse(body.geometry)
    check_size(poly)
    _limit(jobs_limiter, request)
    return veg_out(imagery.start(poly).public())


@router.get("/vegetation/{job_id}")
def vegetation_job(job_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{20}", job_id):
        raise HTTPException(404, "Unknown job")
    j = imagery.get(job_id)
    if j is None:
        raise HTTPException(404, "Unknown or expired job; start it again")
    return veg_out(j.public())


@router.get("")
def list_fields(s: Session = Depends(get_session)) -> list[dict]:
    return [_out(f) for f in s.exec(select(Field_).order_by(Field_.id))]


@router.post("")
def create_field(body: FieldIn, request: Request, s: Session = Depends(get_session)) -> dict:
    _limit(writes_limiter, request)
    poly = parse(body.geometry)
    ha = check_size(poly)
    if s.exec(select(func.count()).select_from(Field_)).one() >= settings.max_saved_fields:
        raise HTTPException(409, "Too many saved fields; delete some first")
    d = describe(poly)
    name = sanitize(body.name, 60) or t("fd_default_name", ha=num(ha, 1))
    f = Field_(farm_id=_farm(s).id, name=name, geometry_geojson=json.dumps(d["geometry"]), area_ha=d["area_ha"],
               commune_id=(d["commune"] or {}).get("id"))
    s.add(f)
    s.commit()
    s.refresh(f)
    return _out(f)


@router.put("/{fid}")
def update_field(fid: int, body: FieldPatch, request: Request, s: Session = Depends(get_session)) -> dict:
    _limit(writes_limiter, request)
    f = s.get(Field_, fid)
    if f is None:
        raise HTTPException(404, "Field not found")
    if body.name is not None:
        f.name = sanitize(body.name, 60) or f.name
    if body.geometry is not None:
        poly = parse(body.geometry)
        check_size(poly)
        d = describe(poly)
        f.geometry_geojson = json.dumps(d["geometry"])
        f.area_ha = d["area_ha"]
        f.commune_id = (d["commune"] or {}).get("id")
    s.add(f)
    s.commit()
    s.refresh(f)
    return _out(f)


@router.delete("/{fid}")
def delete_field(fid: int, request: Request, s: Session = Depends(get_session)) -> dict:
    _limit(writes_limiter, request)
    f = s.get(Field_, fid)
    if f is None:
        raise HTTPException(404, "Field not found")
    for row in [*s.exec(select(FieldPlan).where(FieldPlan.field_id == fid)), *s.exec(select(HarvestReport).where(HarvestReport.field_id == fid))]:
        s.delete(row)  # planner answers and harvest reports belong to the field
    s.delete(f)
    s.commit()
    return {"deleted": fid}


_SKIP = re.compile(r"^Scene ≥ (\d+)% cloud: pixels not read$")
_SPIKE = re.compile(r"^NDVI ([-\d.]+) differs by more than ([\d.]+) from the clear images on (\S+) \(([-\d.]+)\) and (\S+) \(([-\d.]+)\): "
                    r"possible undetected cloud or haze$")


def _note(n: str | None) -> str | None:
    """Imagery notes are stored in English (results are cached); translate when served."""
    if not n:
        return n
    if m := _SKIP.match(n):
        return t("fd_scene_skip", p=m.group(1))
    if m := _SPIKE.match(n):
        return t("fd_spike", v=m.group(1), d=m.group(2), d1=m.group(3), v1=m.group(4), d2=m.group(5), v2=m.group(6))
    if n == "Could not read this image (Earthdata login?)":
        return t("fd_read_error_hls")
    if n == "Could not read this image":
        return t("fd_read_error")
    return L(n)


def veg_out(job: dict) -> dict:
    """Imagery job for the client, with texts in the request's language."""
    if not ro():
        return job
    out = {**job, "error": L(job.get("error"))}
    r = job.get("result")
    if not r:
        return out
    r = localize(r)
    r["index"] = t("fd_index")
    r["status_rules"] = {
        "clear": t("fd_rule_clear", p=f"{imagery.CLEAR_PCT:.0f}"),
        "partly_cloudy": t("fd_rule_partly", a=f"{imagery.PARTLY_PCT:.0f}", b=f"{imagery.CLEAR_PCT:.0f}"),
        "cloudy": t("fd_rule_cloudy", a=f"{imagery.PARTLY_PCT:.0f}", s=f"{imagery.SKIP_CLOUD:.0f}"),
        "no_data": t("fd_rule_nodata"), "error": t("fd_rule_error"),
        "suspect": t("fd_rule_suspect", d=num(imagery.SPIKE_NDVI, 2), days=imagery.SPIKE_DAYS),
    }
    for src in (r.get("sources") or {}).values():
        obs = list(src.get("observations") or [])
        obs += [o for p in (src.get("peaks") or []) for o in (p.get("observations") or [])]
        if src.get("latest_clear"):
            obs.append(src["latest_clear"])
        for o in obs:
            o["note"] = _note(o.get("note"))
    out["result"] = r
    return out
