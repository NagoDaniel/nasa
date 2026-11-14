"""Response language: English by default, Romanian with ?lang=ro; identifiers never translated."""

import re
import string

import pytest
from fastapi.testclient import TestClient

from app import i18n
from app.main import app

client = TestClient(app)
GEOM = {"type": "Polygon", "coordinates": [[[23.66, 46.27], [23.6613, 46.27], [23.6613, 46.2709], [23.66, 46.2709], [23.66, 46.27]]]}


def placeholders(s: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


@pytest.mark.parametrize("key", sorted(i18n.TEMPLATES))
def test_templates_have_same_placeholders(key):
    en, ro = i18n.TEMPLATES[key]
    assert placeholders(en) == placeholders(ro), key


def test_static_has_no_cedilla_diacritics():
    bad = [v for v in list(i18n.STATIC.values()) + [r for _, r in i18n.TEMPLATES.values()] if re.search("[şţŞŢ]", v)]
    assert bad == []


def test_default_is_english_and_unchanged():
    j = client.get("/api/map?kind=agro&key=heat35_jul_aug").json()
    assert j["label"] == "Very hot days (Tmax ≥ 35 °C), Jul–Aug" and j["unit"] == "days"
    assert client.get("/api/map?kind=agro&key=heat35_jul_aug&lang=xx").json()["label"] == j["label"]


def test_romanian_labels_and_units():
    j = client.get("/api/map?kind=agro&key=heat35_jul_aug&lang=ro").json()
    assert j["label"] == "Zile foarte calde (Tmax ≥ 35 °C), iul–aug" and j["unit"] == "zile"
    assert j["key"] == "heat35_jul_aug" and j["kind"] == "agro"  # ids untouched
    c = client.get("/api/map?kind=cropshare&key=216&lang=ro").json()
    assert c["label"] == "Porumb: pondere din terenul arabil"


def test_area_bundle_romanian_keeps_keys():
    a = client.get("/api/area/AB-0001?lang=ro").json()
    assert a["soil"]["properties"]["phh2o"]["label"] == "pH (în apă)"
    assert a["soil"]["values"]["texture"] in i18n.TEXTURES_RO.values()
    assert a["cropmap"]["classes"]["216"] == "porumb"
    assert a["agro_yearly"]["hazards"]["late_frost"]["text"] == "≥ 4 zile cu îngheț în 15 apr–31 mai"
    names = {i["name"] for i in a["indicators"]}
    assert "power_tmax" in names  # identifier kept


def test_rotation_factors_romanian():
    r = client.post("/api/rotations/score?lang=ro", json={"unit": "AB-0001", "rotations": [{"crops": ["maize", "wheat", "maize"]}]}).json()
    res = r["results"][0]
    assert res["crops"] == ["maize", "wheat", "maize"]
    labels = [f["label"] for fs in res["factors"].values() for f in fs]
    assert any(lbl.startswith("porumb: randament local") for lbl in labels)
    assert "−10% aceeași cultură ca în anul precedent (rotația se repetă)" in res["years"][0]["effects"]


def test_procurement_romanian_numbers_and_ids():
    p = client.get("/api/procurement?crop=maize&lang=ro").json()
    assert p["crop"] == "maize" and {r["type"] for r in p["recommendations"]} >= {"spread", "contract"}
    contract = next(r for r in p["recommendations"] if r["type"] == "contract")
    assert contract["title"].startswith("Contractați") and re.search(r"\d\.\d{3} ha", contract["text"])


def test_errors_follow_language():
    bad = {"type": "Point", "coordinates": [23, 46]}
    assert client.post("/api/fields/measure?lang=ro", json={"geometry": bad}).json()["detail"] == "Parcela trebuie să fie un poligon GeoJSON"
    assert client.post("/api/fields/measure", json={"geometry": bad}).json()["detail"] == "Field must be a GeoJSON Polygon"


def test_field_context_romanian():
    c = client.post("/api/fields/context?lang=ro", json={"geometry": GEOM}).json()
    cell = next(d for d in c["cells"] if d["dataset"] == "power_tmax")
    assert cell["label"] == "Temperatura maximă zilnică medie" and cell["kind"] == "surrounding_area_estimate"
    assert cell["note"].startswith("O singură valoare")


def test_localize_leaves_identifiers_and_keys():
    tok = i18n.set_lang("ro")
    try:
        out = i18n.localize({"status": "partly_cloudy", "crop": "maize", "Clay": "Clay", "label": "Clay", "window": "late May–Jun"})
    finally:
        i18n.reset_lang(tok)
    assert out == {"status": "partly_cloudy", "crop": "maize", "Clay": "Argilă", "label": "Argilă", "window": "sfârșit mai–iun"}
