"""Tools the assistant model may call. All read-only and deterministic: they run the
same code the dashboard uses (datasets, map layers, scoring) and return compact JSON
with source, period and confidence. Arguments are validated with Pydantic before use;
invalid arguments come back to the model as an error, never as an exception.

Action tools do not touch anything on the server: they only queue a validated UI action
(select an area, open a section, colour the map) that the browser executes.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .. import datasets as ds
from ..maplayers import map_layer, yearly_layout, yearly_values
from ..scoring.hazards import HAZARDS, crop_hazard_keys, hazard_years
from ..scoring.procurement import procurement
from ..scoring.rotation import score_rotation
from . import places

FARMER_SECTIONS = ("overview", "field", "weather", "risks", "soil", "crops", "rotations")
PROCUREMENT_SECTIONS = ("sourcing", "recs", "trends")
SECTIONS = FARMER_SECTIONS + PROCUREMENT_SECTIONS
B_CROPS = ("oats", "barley", "maize", "pea", "chickpea", "flax", "sunflower")  # direction B (pet food)
METRICS = ("availability", "quality", "impact")
LAYER_KINDS = ("indicator", "agro", "soil", "cropshare")
MAX_ACTIONS = 3

_KEY = r"^[a-z0-9_]{1,40}$"


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _unit_ok(v: str) -> str:
    if not re.fullmatch(r"[A-Z]{1,2}(-\d{4})?", v or "") or places.place(v) is None:
        raise ValueError(f"unknown unit id '{v}'; call find_area first")
    return v


class UnitArgs(Args):
    unit_id: str

    @field_validator("unit_id")
    @classmethod
    def _unit(cls, v: str) -> str:
        return _unit_ok(v)


class FindArea(Args):
    name: str = Field(min_length=2, max_length=60)


class IndicatorArgs(UnitArgs):
    indicator: str = Field(pattern=_KEY)
    year: int | None = Field(None, ge=2000, le=2030)


class SeasonArgs(UnitArgs):
    year: int | None = Field(None, ge=2000, le=2030)


class CropStatsArgs(Args):
    county: str = Field(pattern=r"^[A-Z]{1,2}$|^RO$")
    crop: str | None = Field(None, pattern=_KEY)


class ProcArgs(Args):
    crop: str = Field(pattern=_KEY)
    county: str | None = Field(None, pattern=r"^[A-Z]{1,2}$")


class Prio(Args):
    yield_: float = Field(25, alias="yield", ge=0, le=100)
    water: float = Field(25, ge=0, le=100)
    soil: float = Field(25, ge=0, le=100)
    risk: float = Field(25, ge=0, le=100)


class RotationArgs(UnitArgs):
    rotations: list[list[str]] = Field(min_length=1, max_length=3)
    priorities: Prio | None = None

    @field_validator("rotations")
    @classmethod
    def _rot(cls, v: list[list[str]]) -> list[list[str]]:
        for r in v:
            if not 3 <= len(r) <= 4:
                raise ValueError("each rotation needs 3 or 4 crops (one per year)")
        return v


class RankArgs(Args):
    kind: Literal["indicator", "agro", "soil", "cropshare"]
    key: str = Field(pattern=_KEY)
    year: str | None = Field(None, pattern=r"^\d{4}$")
    level: Literal["county", "commune"] = "commune"
    county: str | None = Field(None, pattern=r"^[A-Z]{1,2}$")
    order: Literal["desc", "asc"] = "desc"
    top: int = Field(5, ge=1, le=10)


class TraitArgs(Args):
    crop: str = Field(pattern=_KEY)


class SectionArgs(Args):
    section: Literal[SECTIONS]  # type: ignore[valid-type]


class ColorArgs(Args):
    kind: Literal["indicator", "agro", "soil", "cropshare"]
    key: str = Field(pattern=_KEY)
    year: str | None = Field(None, pattern=r"^\d{4}$")


class ProcCropArgs(Args):
    crop: Literal[B_CROPS]  # type: ignore[valid-type]
    metric: Literal["availability", "quality", "impact"] | None = None


class NoArgs(Args):
    pass


# ----------------------------------------------------------------------------- helpers
def _conf(meta: dict, kind: str) -> dict:
    c = meta.get("confidence") or {}
    return {"level": c.get(kind, "n/a"), "note": c.get("note")}


def _unit(uid: str) -> dict:
    u = ds.require_unit(uid)
    p = places.place(uid)
    return {"id": uid, "name": u["name"], "kind": u["kind"], "county": u["county"],
            "county_name": p.county_name if p else u["county"], "area_km2": u.get("area_km2")}


def _soil_brief(uid: str) -> dict | None:
    s = ds.soil(uid)
    v = s.get("values")
    if not v:
        return None
    return {"texture": v.get("texture"), "ph": (v.get("phh2o") or {}).get("median"),
            "soc_g_kg": (v.get("soc") or {}).get("median"), "clay_pct": (v.get("clay") or {}).get("median"),
            "sand_pct": (v.get("sand") or {}).get("median"), "source": s["source"], "depth": s.get("depth")}


def _latest_hazards(uid: str) -> dict:
    a = ds.agro(uid)
    years, vals = a["years"], a["values"]
    keys = [k for k in HAZARDS if vals.get(k)]
    hy = hazard_years(keys, vals, years)
    with_data = [y for i, y in enumerate(years) if any((vals.get(k) or [None] * len(years))[i] is not None for k in keys)]
    last = max(with_data) if with_data else None
    return {"latest_year_with_data": last,
            "hazards_hit": [HAZARDS[k].text for k in hy.get(last, [])] if last else [],
            "hazard_years_count": {k: sum(1 for y in with_data if k in hy[y]) for k in keys},
            "years_with_data": [min(with_data), max(with_data)] if with_data else None}


# ----------------------------------------------------------------------------- data tools
def find_area(a: FindArea, _: dict) -> dict:
    hits = places.resolve(a.name)
    if not hits:
        return {"matches": [], "note": "No county or commune with this name in the study area "
                "(Alba, Arad, Bihor, Cluj, Hunedoara, Mureș, Sibiu, Vâlcea)."}
    return {"matches": [p.as_dict() for p in hits],
            "note": "Several areas share this name; ask the user which one." if len(hits) > 1 else None}


def area_summary(a: UnitArgs, _: dict) -> dict:
    uid = a.unit_id
    out: dict[str, Any] = {"unit": _unit(uid), "soil": _soil_brief(uid), "season_hazards": _latest_hazards(uid)}
    t = ds.terrain(uid)
    if t:
        v = t["values"]
        out["terrain"] = {"elevation_m": v.get("elevation_m"), "cropland_share_pct": (v.get("landcover_pct") or {}).get("40"),
                          "forest_share_pct": (v.get("landcover_pct") or {}).get("10"),
                          "cropland_slope_pct": v.get("cropland_slope_pct"), "source": t["sources"]}
    cm = ds.cropmap(uid)
    if cm and cm.get("values"):
        y = max(cm["values"])
        classes = {c: n for c, n in cm["values"][y].items() if 200 <= int(c) < 300}
        tot = sum(classes.values())
        if tot:
            top = sorted(classes.items(), key=lambda x: -x[1])[:5]
            out["crop_mix"] = {"year": y, "source": cm["source"], "arable_ha": round(tot),
                               "top": [{"crop": cm["classes"][c], "ha": round(n), "share_pct": round(100 * n / tot, 1)} for c, n in top]}
    out["confidence"] = "Soil 250 m (fits communes); weather from 25–50 km grids (regional for communes)."
    return out


def indicator_series(a: IndicatorArgs, _: dict) -> dict:
    if a.indicator not in ds.indicator_names():
        return {"error": f"unknown indicator '{a.indicator}'", "valid": ds.indicator_names()}
    d = ds.store.get(f"nasa/{a.indicator}.json")
    arr = d["units"].get(a.unit_id)
    meta = {"indicator": a.indicator, "label": d["label"], "unit": d["unit"], "source": d["source"],
            "resolution": d.get("resolution"), "period": d.get("period"), "aggregation": d.get("aggregation"),
            "confidence": _conf(d, places.place(a.unit_id).kind), "area": _unit(a.unit_id)}
    if arr is None:
        return {**meta, "error": "no data for this area"}
    if a.year:
        months = {k: v for k, v in zip(d["keys"], arr) if k.startswith(str(a.year))}
        if not months:
            return {**meta, "error": f"no data for {a.year}"}
        return {**meta, "year": a.year, "monthly": months}
    layout = yearly_layout(d)
    vals = yearly_values(arr, layout)
    clean = [v for v in vals if v is not None]
    return {**meta, "yearly_unit": f"{d['unit']}/yr" if layout[3] else d["unit"],
            "yearly": dict(zip(layout[0], vals)),
            "mean_of_complete_years": round(sum(clean) / len(clean), 2) if clean else None,
            "note": "Only complete years are listed; per year = sum of months for amounts, mean for states."}


def season_hazards(a: SeasonArgs, _: dict) -> dict:
    d = ds.agro(a.unit_id)
    years = d["years"]
    if a.year and a.year not in years:
        return {"error": f"no season data for {a.year}", "years": years}
    idx = [years.index(a.year)] if a.year else range(len(years))
    out = {}
    for k, meta in d["indicators"].items():
        series = d["values"].get(k) or []
        vals = {str(years[i]): (series[i] if i < len(series) else None) for i in idx}
        row: dict[str, Any] = {"label": meta["label"], "unit": meta["unit"], "values": vals}
        if k in HAZARDS:
            h = HAZARDS[k]
            row["hazard_threshold"] = h.text
            row["hazard_years"] = [y for y, v in vals.items() if v is not None and (v >= h.threshold if h.op == ">=" else v <= h.threshold)]
        out[k] = row
    return {"area": _unit(a.unit_id), "indicators": out,
            "confidence": _conf(d, places.place(a.unit_id).kind),
            "source": "NASA POWER daily (~50 km) + NASA GLDAS Noah monthly (~25 km), crop windows computed in this project",
            "threshold_note": "Heat thresholds are physiological; rain / wet-day / dry-spell thresholds ≈ regional 75th percentile 2015–2025."}


def soil_profile(a: UnitArgs, _: dict) -> dict:
    s = ds.soil(a.unit_id)
    if not s.get("values"):
        return {"area": _unit(a.unit_id), "error": "no soil data for this area"}
    return {"area": _unit(a.unit_id), "source": s["source"], "depth": s.get("depth"), "resolution": s.get("resolution"),
            "statistic": s.get("statistic"), "properties": s["properties"], "values": s["values"],
            "confidence": _conf(s, places.place(a.unit_id).kind)}


def crop_stats(a: CropStatsArgs, _: dict) -> dict:
    d = ds.ins()
    c = d["counties"].get(a.county)
    if c is None:
        return {"error": f"no statistics for '{a.county}'", "valid": sorted(d["counties"])}
    base = {"county": a.county, "years": d["years"], "source": d["source"], "confidence": d.get("confidence")}
    if a.crop:
        key = "grain_legumes" if a.crop == "chickpea" else a.crop
        if key not in c:
            return {**base, "error": f"no statistics for crop '{a.crop}'", "valid": sorted(c)}
        return {**base, "crop": key, "series": c[key],
                "note": "Chickpea has no INS statistics; grain legumes used as proxy (low confidence)." if a.crop == "chickpea" else None}
    latest = {}
    for crop, rec in c.items():
        last = {m: next((x for x in reversed(rec.get(m) or []) if x is not None), None) for m in ("area_ha", "production_t", "yield_kg_ha")}
        latest[crop] = last
    return {**base, "latest_values": latest, "note": "Latest available year per series; call again with crop for the full series."}


def procurement_for_crop(a: ProcArgs, _: dict) -> dict:
    traits = ds.traits()
    if a.crop not in traits["crops"]:
        return {"error": f"unknown crop '{a.crop}'", "valid": sorted(traits["crops"])}
    counties, agro_all, fires, ndvi = ds.procurement_inputs()
    p = procurement(a.crop, counties, ds.ins(), agro_all, traits, fires, ndvi)
    if a.county:
        c = p["counties"].get(a.county)
        if c is None:
            return {"error": f"'{a.county}' is not a study-area county", "valid": sorted(p["counties"])}
        c = {**c, "availability": {k: v for k, v in c["availability"].items() if k != "series"}}
        return {"crop": a.crop, "proxy": p["proxy"], "county": a.county, "metrics": c,
                "assumptions": p["assumptions"], "sources": p["sources"]}
    table = {code: {"name": c["name"], "availability": c["availability"]["score"], "quality": c["quality"]["score"],
                    "impact": c["impact"]["score"], "production_t_median_5y": c["availability"]["production_t_median_5y"],
                    "latest_quality_year": c["quality"]["latest_year"], "latest_hits": c["quality"]["latest_hits"],
                    "confidence": c["confidence"]} for code, c in p["counties"].items()}
    return {"crop": a.crop, "proxy": p["proxy"], "counties": table,
            "recommendations": [{"title": r["title"], "text": r["text"]} for r in p["recommendations"]],
            "assumptions": p["assumptions"], "sources": p["sources"], "score_scale": "0–100, higher is better"}


def score_rotations(a: RotationArgs, _: dict) -> dict:
    traits = ds.traits()["crops"]
    bad = sorted({c for r in a.rotations for c in r if c not in traits})
    if bad:
        return {"error": f"unknown crops {bad}", "valid": sorted(traits)}
    ctx = ds.rotation_context(a.unit_id)
    prio = (a.priorities or Prio()).model_dump(by_alias=True)
    results = []
    for r in a.rotations:
        s = score_rotation(ctx, r, prio)
        results.append({"crops": r, "total": s["total"], "scores": s["scores"], "weights": s["weights"],
                        "years": [{k: y[k] for k in ("year", "crop", "yield", "water", "risk", "expected_yield_kg_ha", "effects")} for y in s["years"]],
                        "factors": {k: [{"label": f["label"], "value": f["value"], "effect": f["effect"]} for f in v] for k, v in s["factors"].items()},
                        "confidence": s["confidence"]})
    return {"area": _unit(a.unit_id), "priorities": prio, "results": results,
            "score_scale": "0–100, higher is better; total = priority-weighted mean of yield, water, soil, risk"}


def rank_areas(a: RankArgs, _: dict) -> dict:
    try:
        layer = map_layer(a.kind, a.key)
    except HTTPException as e:
        return {"error": str(e.detail)}
    years = layer["years"]
    if years and a.year and a.year not in years:
        return {"error": f"no {a.year} for this layer", "years": years}
    i = years.index(a.year) if years and a.year else (len(years) - 1 if years else 0)
    rows = []
    for uid, vals in layer["values"].items():
        p = places.place(uid)
        if p is None or p.kind != a.level or (a.county and p.county != a.county):
            continue
        v = vals[i] if i < len(vals) else None
        if v is not None:
            rows.append({"id": uid, "name": p.name, "county": p.county_name, "value": v})
    rows.sort(key=lambda r: r["value"], reverse=a.order == "desc")
    return {"layer": layer["label"], "unit": layer["unit"], "year": years[i] if years else None,
            "level": a.level, "county_filter": a.county, "areas_ranked": len(rows), "top": rows[:a.top],
            "source": layer["source"]}


def crop_traits(a: TraitArgs, _: dict) -> dict:
    t = ds.traits()
    if a.crop not in t["crops"]:
        return {"error": f"unknown crop '{a.crop}'", "valid": sorted(t["crops"])}
    return {"crop": a.crop, "traits": t["crops"][a.crop], "note": t.get("note")}


_catalog_cache: dict = {}


def catalog() -> dict:
    """Valid keys for map layers and tools (also embedded in the system instruction)."""
    agro = ds.store.get("derived/agro_yearly.json")
    if _catalog_cache.get("src") is agro:
        return _catalog_cache["data"]
    nasa = {}
    for n in ds.indicator_names():
        d = ds.store.get(f"nasa/{n}.json")
        nasa[n] = f"{d['label']} [{d['unit']}] — {d['source'].split('(')[0].strip()}, {d.get('resolution', '')}"
    soil = ds.store.get("soil/soilgrids.json")["properties"]
    cm = ds.store.get("crops/cropmap.json")["classes"]
    data = {
        "indicator (monthly NASA series)": nasa,
        "agro (yearly crop-window indicators)": {k: f"{v['label']} [{v['unit']}]" for k, v in agro["indicators"].items()},
        "soil (SoilGrids 0–30 cm)": {k: f"{v['label']} [{v['unit']}]" for k, v in soil.items()},
        "cropshare (EUCROPMAP class codes, years 2018/2022)": {k: v for k, v in cm.items() if 200 <= int(k) < 300},
        "crops (traits / rotations / INS)": sorted(ds.traits()["crops"]),
        "direction B ingredient crops (procurement)": list(B_CROPS),
        "sections": {"farmer": list(FARMER_SECTIONS), "procurement": list(PROCUREMENT_SECTIONS)},
        "counties": {u["id"]: u["name"] for u in ds.units_index().values() if u["kind"] == "county"},
    }
    _catalog_cache.update(src=agro, data=data)
    return data


def list_layers(_: NoArgs, __: dict) -> dict:
    return catalog()


# ----------------------------------------------------------------------------- action tools
def _queue(state: dict, action: dict) -> dict:
    acts: list[dict] = state.setdefault("actions", [])
    acts[:] = [x for x in acts if x["type"] != action["type"]]  # one per type, last wins
    if len(acts) >= MAX_ACTIONS:
        return {"ok": False, "error": "too many actions in one reply"}
    acts.append(action)
    return {"ok": True, "queued": action, "note": "The dashboard will do this when your reply is shown."}


def select_area(a: UnitArgs, state: dict) -> dict:
    return _queue(state, {"type": "select_area", "unit_id": a.unit_id})


def open_section(a: SectionArgs, state: dict) -> dict:
    return _queue(state, {"type": "open_section", "section": a.section})


def color_map(a: ColorArgs, state: dict) -> dict:
    try:
        layer = map_layer(a.kind, a.key)
    except HTTPException as e:
        return {"ok": False, "error": str(e.detail)}
    years = layer["years"]
    if a.year and years and a.year not in years:
        return {"ok": False, "error": f"year {a.year} not available", "years": years}
    return _queue(state, {"type": "color_map", "kind": a.kind, "key": a.key, "year": a.year if years else None})


def set_procurement_crop(a: ProcCropArgs, state: dict) -> dict:
    return _queue(state, {"type": "set_procurement_crop", "crop": a.crop, "metric": a.metric})


# ----------------------------------------------------------------------------- registry
STR = {"type": "string"}
INT = {"type": "integer"}
UNIT = {"type": "string", "description": "Unit id from find_area, e.g. 'AB' (county) or 'AB-0001' (commune)."}
YEAR_S = {"type": "string", "description": "Four-digit year, e.g. '2024'."}

TOOLS: dict[str, tuple[Callable[[Any, dict], dict], type[Args], str, dict]] = {
    "find_area": (find_area, FindArea, "Resolve a county or commune name (any spelling, with or without diacritics) to unit ids.",
                  {"type": "object", "properties": {"name": STR}, "required": ["name"]}),
    "area_summary": (area_summary, UnitArgs, "Overview of one area: soil, terrain, crop mix, latest season's weather hazards.",
                     {"type": "object", "properties": {"unit_id": UNIT}, "required": ["unit_id"]}),
    "indicator_series": (indicator_series, IndicatorArgs,
                         "Yearly values of a NASA indicator for an area (or the 12 monthly values of one year if year is given).",
                         {"type": "object", "properties": {"unit_id": UNIT, "indicator": STR, "year": INT}, "required": ["unit_id", "indicator"]}),
    "season_hazards": (season_hazards, SeasonArgs,
                       "Yearly crop-window indicators (heat at maize flowering, wet small-grain flowering, late frost, harvest rain, dry spells, water balance…) with hazard thresholds and the years they were crossed.",
                       {"type": "object", "properties": {"unit_id": UNIT, "year": INT}, "required": ["unit_id"]}),
    "soil_profile": (soil_profile, UnitArgs, "SoilGrids 0–30 cm soil properties (median, p10, p90) and texture for an area.",
                     {"type": "object", "properties": {"unit_id": UNIT}, "required": ["unit_id"]}),
    "crop_stats": (crop_stats, CropStatsArgs, "INS county statistics: area, production, yield per crop 2015–2025. county = county code or 'RO'.",
                   {"type": "object", "properties": {"county": STR, "crop": STR}, "required": ["county"]}),
    "procurement_for_crop": (procurement_for_crop, ProcArgs,
                             "Procurement view for an ingredient crop: availability / quality / impact scores per county, recommendations, assumptions. Optional county code for details.",
                             {"type": "object", "properties": {"crop": STR, "county": STR}, "required": ["crop"]}),
    "score_rotations": (score_rotations, RotationArgs,
                        "Score 1–3 crop rotations (3–4 crops each, one per year) for an area with farmer priorities (yield, water, soil, risk weights). Returns scores with explaining factors.",
                        {"type": "object", "properties": {
                            "unit_id": UNIT,
                            "rotations": {"type": "array", "items": {"type": "array", "items": STR}},
                            "priorities": {"type": "object", "properties": {"yield": {"type": "number"}, "water": {"type": "number"}, "soil": {"type": "number"}, "risk": {"type": "number"}}},
                        }, "required": ["unit_id", "rotations"]}),
    "rank_areas": (rank_areas, RankArgs, "Rank communes or counties by a map layer value in one year (e.g. most heat days in 2024 in Alba).",
                   {"type": "object", "properties": {
                       "kind": {"type": "string", "enum": list(LAYER_KINDS)}, "key": STR, "year": YEAR_S,
                       "level": {"type": "string", "enum": ["county", "commune"]}, "county": STR,
                       "order": {"type": "string", "enum": ["desc", "asc"]}, "top": INT,
                   }, "required": ["kind", "key"]}),
    "crop_traits": (crop_traits, TraitArgs, "Crop characteristics: water need, heat sensitivity, sensitive stage, legume / N fixation, references.",
                    {"type": "object", "properties": {"crop": STR}, "required": ["crop"]}),
    "list_layers": (list_layers, NoArgs, "All valid indicator, agro, soil and crop-class keys, crops, sections and counties.",
                    {"type": "object", "properties": {}}),
    # actions (executed by the dashboard)
    "select_area": (select_area, UnitArgs, "ACTION: select an area on the dashboard and zoom the map to it.",
                    {"type": "object", "properties": {"unit_id": UNIT}, "required": ["unit_id"]}),
    "open_section": (open_section, SectionArgs, "ACTION: open a dashboard section.",
                     {"type": "object", "properties": {"section": {"type": "string", "enum": list(SECTIONS)}}, "required": ["section"]}),
    "color_map": (color_map, ColorArgs, "ACTION: colour the map by a layer (and year) and open the matching farmer section.",
                  {"type": "object", "properties": {"kind": {"type": "string", "enum": list(LAYER_KINDS)}, "key": STR, "year": YEAR_S},
                   "required": ["kind", "key"]}),
    "set_procurement_crop": (set_procurement_crop, ProcCropArgs, "ACTION: open the procurement sourcing view for an ingredient crop (and score).",
                             {"type": "object", "properties": {"crop": {"type": "string", "enum": list(B_CROPS)},
                                                               "metric": {"type": "string", "enum": list(METRICS)}}, "required": ["crop"]}),
}


def declarations() -> list[dict]:
    return [{"name": n, "description": d, "parameters_json_schema": s} for n, (_, _, d, s) in TOOLS.items()]


def execute(name: str, args: dict, state: dict) -> dict:
    """Run one tool call from the model. Never raises."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"unknown tool '{name}'"}
    fn, model, _, _ = spec
    try:
        parsed = model.model_validate(args or {})
    except ValidationError as e:
        return {"error": "invalid arguments", "details": [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:5]]}
    try:
        return fn(parsed, state)
    except HTTPException as e:
        return {"error": str(e.detail)}
    except Exception:  # noqa: BLE001 – the model gets a generic error, details stay in the server log
        import logging
        logging.getLogger(__name__).exception("assistant tool %s failed", name)
        return {"error": "internal error while reading the data"}
