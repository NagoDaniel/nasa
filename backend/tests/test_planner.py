"""Field planner: learning from reports, rotation rules, timing, and the planner API (temporary DB)."""

import math

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import datasets as ds
from app.db import get_session
from app.main import app
from app.planner import climate as C
from app.planner import learning as L
from app.planner.plan import _gaps_ok, allowed_crops
from app.routers import fields as fields_router
from app.routers import planner as planner_router


def square(lon=23.66, lat=46.27, dx=0.013, dy=0.009):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + dx, lat], [lon + dx, lat + dy], [lon, lat + dy], [lon, lat]]]}


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = session
    monkeypatch.setattr(fields_router, "writes_limiter", fields_router.RateLimiter(1000, 1000, 0))
    monkeypatch.setattr(planner_router, "writes", planner_router.RateLimiter(1000, 1000, 0))
    yield TestClient(app)
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------------- learning
def test_field_level_is_shrunk_toward_the_county():
    exp = lambda crop, county, year: 5000.0  # noqa: E731
    one = L.field_level([{"field_id": 1, "year": 2025, "crop": "maize", "yield_t_ha": 6.0, "county": "AB"}], exp)
    assert one["raw_pct"] == pytest.approx(20.0) and 0 < one["pct"] < 20 and one["weight"] == 0.25
    many = L.field_level([{"field_id": 1, "year": y, "crop": "maize", "yield_t_ha": 6.0, "county": "AB"} for y in range(2010, 2022)], exp)
    assert many["pct"] > one["pct"] and many["factor"] == pytest.approx(math.exp(12 / 15 * math.log(1.2)))
    assert L.field_level([], exp)["factor"] == 1.0


def test_shared_effect_moves_from_literature_toward_reports():
    traits = ds.traits()
    exp = lambda crop, county, year: 5000.0  # noqa: E731
    reps = []
    for f in range(20):  # wheat after pea yields 30 % more than wheat after maize on every field
        reps += [{"field_id": f, "year": 2020, "crop": "pea", "yield_t_ha": 2.0, "county": "AB"},
                 {"field_id": f, "year": 2021, "crop": "wheat", "yield_t_ha": 6.5, "county": "AB"},
                 {"field_id": f, "year": 2022, "crop": "maize", "yield_t_ha": 5.0, "county": "AB"},
                 {"field_id": f, "year": 2023, "crop": "wheat", "yield_t_ha": 5.0, "county": "AB"}]
    e = L.shared_effects(reps, exp, traits)["legume_precrop_yield_bonus"]
    assert e["measured"] == pytest.approx(0.3, abs=1e-6) and e["n"] == 20
    assert e["literature"] < e["used"] < e["measured"]
    assert L.shared_effects([], exp, traits)["legume_precrop_yield_bonus"]["used"] == e["literature"]


# ----------------------------------------------------------------------------- rules
def test_allowed_crops_follow_machinery_and_nitrogen():
    traits = ds.traits()
    crops, why = allowed_crops({"planter": False, "n_limit": 100, "avoid": ["oats"]}, traits)
    assert not {"maize", "sunflower", "soy", "oats"} & set(crops) and "pea" in crops and why


def test_return_gaps_include_what_grew_before():
    traits = ds.traits()
    gap = traits["crops"]["sunflower"]["min_return_years"]
    assert gap > 1
    assert not _gaps_ok(("sunflower", "wheat", "pea", "barley"), {2026: "sunflower"}, 2027, traits)
    assert _gaps_ok(("wheat", "pea", "barley", "maize"), {2026: "sunflower"}, 2027, traits)


def test_sowing_and_maturity_timing_for_alba():
    inputs = ds.store.get("derived/forecast_inputs.json")
    t = ds.traits()["crops"]["maize"]
    clim = inputs["climate"]["counties"]["AB"]
    sow = C.sowing("maize", t, clim, inputs["years"])
    assert 90 < sow["start_doy"] <= sow["safe_doy"] < 160  # April–May
    cls, opts = C.suggest_maturity("maize", t, clim, inputs["years"], sow)
    assert cls in ("early", "medium", "late") and [o["gdd10"] for o in opts] == sorted(o["gdd10"] for o in opts)
    assert opts[0]["before_frost_share"] >= opts[-1]["before_frost_share"]


# ----------------------------------------------------------------------------- API
def test_plan_report_and_learning_api(client):
    fid = client.post("/api/fields", json={"name": "Plan test", "geometry": square()}).json()["id"]
    ans = {"history": [{"year": 2025, "crop": "maize", "yield_t_ha": 6.0}, {"year": 2026, "crop": "wheat", "yield_t_ha": 5.0}],
           "consider": ["maize", "wheat", "pea", "sunflower", "barley"], "contract_crop": "pea", "years": 4}
    r = client.post(f"/api/planner/fields/{fid}/plan", json=ans)
    assert r.status_code == 200, r.text
    j = r.json()
    plans = j["plan"]["plans"]
    assert 1 <= len(plans) <= 3 and all(len(p["crops"]) == 4 for p in plans)
    assert plans[0]["years"][0]["year"] == j["plan"]["start_year"] and plans[0]["years"][0]["previous"] == "wheat"
    assert j["learning"]["field"]["n"] == 2  # past seasons count as reports
    y = plans[0]["years"][0]
    assert y["yield"]["range_t_ha"]["80"][0] <= y["yield"]["t_ha"] <= y["yield"]["range_t_ha"]["80"][1]
    assert client.get(f"/api/planner/fields/{fid}").json()["answers"]["contract_crop"] == "pea"
    rr = client.post(f"/api/planner/fields/{fid}/reports", json={"year": 2026, "crop": "wheat", "yield_t_ha": 6.5, "problems": ["hail"]})
    assert rr.status_code == 200 and rr.json()["learning"]["field"]["n"] == 2
    assert client.get("/api/planner/learning").json()["n_reports"] == 2
    assert client.post(f"/api/planner/fields/{fid}/plan", json={**ans, "consider": ["sunflower"], "avoid": ["sunflower"]}).json()["plan"]["error"]
    assert client.delete(f"/api/fields/{fid}").status_code == 200
    assert client.get("/api/planner/learning").json()["n_reports"] == 0
    assert client.post("/api/planner/fields/999/plan", json=ans).status_code == 404
    assert client.post(f"/api/planner/fields/{fid}/plan", json={**ans, "bogus": 1}).status_code in (404, 422)
