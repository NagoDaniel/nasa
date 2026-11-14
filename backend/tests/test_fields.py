"""Drawn fields: geometry validation, surrounding-area cells, soil pixels, the undetected-
cloud check, and the saved-field API (temporary database; no network)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.field import coarse, geom
from app.field.imagery import finalize, flag_spikes
from app.main import app
from app.routers import fields as fields_router


def square(lon=23.66, lat=46.27, dx=0.0013, dy=0.0009):
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
    yield TestClient(app)
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------------- geometry
def test_area_and_commune_of_one_hectare():
    p = geom.parse(square())
    assert geom.area_ha(p) == pytest.approx(1.0, abs=0.02)
    d = geom.describe(p)
    assert d["commune"]["id"] == "AB-0001" and d["commune"]["share_pct"] == 100.0


@pytest.mark.parametrize("g,msg", [
    ({"type": "Point", "coordinates": [23, 46]}, "Polygon"),
    ({"type": "Polygon", "coordinates": [[[23.66, 46.27], [23.661, 46.271], [23.661, 46.27], [23.66, 46.271], [23.66, 46.27]]]}, "crosses"),
    (square(lon=10.0, lat=50.0), "Romania"),
    ({"type": "Polygon", "coordinates": [[[23.66, 46.27], [23.661, 46.27], [23.66, 46.27]]]}, "corners"),
    ({"type": "Polygon", "coordinates": [[[23.66, 46.27], ["x", 46.27], [23.661, 46.271], [23.66, 46.27]]]}, "Invalid"),
])
def test_invalid_geometries(g, msg):
    with pytest.raises(Exception) as e:
        geom.parse(g)
    assert msg in str(e.value.detail)


def test_size_limits():
    with pytest.raises(Exception, match="minimum"):
        geom.check_size(geom.parse(square(dx=0.0003, dy=0.0003)))
    with pytest.raises(Exception, match="maximum"):
        geom.check_size(geom.parse(square(dx=1.5, dy=0.6)))


def test_geom_key_ignores_ring_start_and_direction():
    a = geom.parse(square())
    ring = square()["coordinates"][0][:-1]
    b = geom.parse({"type": "Polygon", "coordinates": [list(reversed(ring[1:] + ring[:1])) + [list(reversed(ring[1:] + ring[:1]))[0]]]})
    assert geom.geom_key(a) == geom.geom_key(b)


# ----------------------------------------------------------------------------- coarse data
def test_cells_are_native_and_labelled_as_estimates():
    p = geom.parse(square())
    c = coarse.cell_context("power_tmax", p)
    assert c["kind"] == "surrounding_area_estimate" and "~50 km" in c["resolution"]
    (cell,) = c["cells"]
    assert cell["share_of_field_pct"] == 100.0 and cell["field_share_of_cell_pct"] < 0.001
    assert cell["cell_area_km2"] > 2000 and cell["yearly"]


def test_two_fields_in_one_cell_get_identical_values():
    """A smaller or shifted selection inside the same cell must not produce a different 'more precise' value."""
    a = coarse.cell_context("power_precip", geom.parse(square()))
    b = coarse.cell_context("power_precip", geom.parse(square(lon=23.70, lat=46.30, dx=0.01, dy=0.01)))
    assert a["cells"][0]["cell"] == b["cells"][0]["cell"]
    assert a["cells"][0]["yearly"] == b["cells"][0]["yearly"]


def test_field_on_cell_border_lists_each_cell():
    c = coarse.cell_context("imerg_precip", geom.parse(square(lon=23.69, lat=46.29, dx=0.02, dy=0.01)))
    assert len(c["cells"]) == 2
    assert sum(x["share_of_field_pct"] for x in c["cells"]) == pytest.approx(100, abs=0.5)


@pytest.mark.skipif(not coarse.soil_dir_exists(), reason="SoilGrids rasters not on this machine")
def test_soil_pixels_and_no_data_in_town():
    s = coarse.soil_context(geom.parse(square()))
    assert s["status"] == "ok" and s["pixels"]["count"] >= 1 and s["pixels"]["pixel_area_ha"] > 3
    assert 4 < s["values"]["phh2o"]["mean"] < 9
    town = coarse.soil_context(geom.parse(square(lon=23.716, lat=46.305)))
    assert town["status"] == "no_data"


# ----------------------------------------------------------------------------- undetected cloud check
def obs(day, v, status="clear", src="s2"):
    return {"date": day, "status": status, "item_id": f"{src}{day}", "ndvi": None if v is None else {"median": v}}


def test_spike_between_clear_neighbours_is_flagged_and_skipped_for_latest():
    s2 = [obs("2026-10-19", 0.60), obs("2026-10-24", 0.07), obs("2026-11-01", None, "cloudy")]
    hls = [obs("2026-10-25", 0.58, src="hls")]
    out = finalize({"s2": {"status": "ok", "observations": s2, "_overlays": {"s22026-10-19": {"x": 1}, "s22026-10-24": {"x": 2}}},
                    "hls": {"status": "ok", "observations": hls, "_overlays": {}}})
    st = {o["date"]: o["status"] for o in out["s2"]["observations"]}
    assert st["2026-10-24"] == "suspect" and st["2026-10-19"] == "clear"
    assert out["s2"]["counts"] == {"clear": 1, "suspect": 1, "cloudy": 1}
    assert out["s2"]["latest_clear"]["date"] == "2026-10-19"
    assert out["hls"]["latest_clear"] is None


def test_real_changes_are_not_flagged():
    # harvest: a drop that stays low is not a spike; gaps longer than the window are not judged
    s = [obs("2026-07-01", 0.8), obs("2026-07-08", 0.2), obs("2026-07-15", 0.18), obs("2026-09-01", 0.6)]
    flag_spikes({"s2": {"observations": s}})
    assert all(o["status"] == "clear" for o in s)


# ----------------------------------------------------------------------------- API
def test_saved_field_crud(client):
    r = client.post("/api/fields", json={"name": "North plot", "geometry": square()})
    assert r.status_code == 200 and r.json()["area_ha"] == pytest.approx(1.0, abs=0.02)
    fid = r.json()["id"]
    assert [f["name"] for f in client.get("/api/fields").json()] == ["North plot"]
    r = client.put(f"/api/fields/{fid}", json={"geometry": square(dx=0.0026)})
    assert r.json()["area_ha"] == pytest.approx(2.0, abs=0.05)
    assert client.delete(f"/api/fields/{fid}").json() == {"deleted": fid}
    assert client.get("/api/fields").json() == []
    assert client.delete(f"/api/fields/{fid}").status_code == 404


def test_api_rejects_bad_input(client):
    assert client.post("/api/fields", json={"name": "x", "geometry": square(dx=0.0002, dy=0.0002)}).status_code == 422
    assert client.post("/api/fields", json={"name": "x" * 61, "geometry": square()}).status_code == 422
    assert client.post("/api/fields", json={"name": "x", "geometry": square(), "admin": 1}).status_code == 422
    big = {"type": "Polygon", "coordinates": [[[23.66 + i * 1e-5, 46.27] for i in range(6000)]]}
    assert client.post("/api/fields/measure", json={"geometry": big}).status_code == 413
    assert client.get("/api/fields/vegetation/not-a-job").status_code == 404


def test_measure_and_context(client):
    m = client.post("/api/fields/measure", json={"geometry": square(dx=0.001, dy=0.0007)}).json()
    assert m["area_ha"] < 1 and any("Under 1 ha" in w for w in m["warnings"])
    c = client.post("/api/fields/context", json={"geometry": square()}).json()
    assert {d["dataset"] for d in c["cells"]} >= {"imerg_precip", "power_tmax", "gldas_rootmoist"}
    assert all(d["kind"] == "surrounding_area_estimate" for d in c["cells"])
