import json
from pathlib import Path

import pytest

from app.scoring.hazards import cv, hazard_years, is_hazard, median, percentile
from app.scoring.rotation import Context, score_rotation

TRAITS = json.loads((Path(__file__).parents[1] / "data/crops/crop_traits.json").read_text())
YEARS = list(range(2015, 2026))


def ctx(**over):
    agro = {
        "precip_apr_sep": [450.0] * 11,
        "heat35_jul_aug": [0, 0, 5, 0, 0, 0, 0, 4, 0, 0, 0],  # 2 hazard years
        "rootmoist_jja_z": [0.0] * 11,
        "dry_spell_apr_sep": [10.0] * 11,
        "rain_harvest_summer_crops": [100.0] * 11,
        "rain_flowering_small_grain": [150.0] * 11,
        "wet_days_flowering_small_grain": [20.0] * 11,
        "rain_harvest_small_grain": [60.0] * 11,
        "heat30_jun": [1.0] * 11,
        "heat32_jul_aug": [5.0] * 11,
        "late_frost": [0.0] * 11,
    }
    y = lambda v: {"yield_kg_ha": [v] * 11}
    base = dict(
        unit={"id": "AB", "kind": "county"},
        agro={"years": YEARS, "values": agro},
        soil={"phh2o": {"median": 6.5}, "soc": {"median": 30.0}},
        ins_county={c: y(v) for c, v in {"maize": 6000, "wheat": 4500, "barley": 4000, "oats": 2500, "pea": 2000,
                                         "sunflower": 2500, "soy": 2200, "flax": 1500, "grain_legumes": 1800}.items()},
        ins_ro={c: y(v) for c, v in {"maize": 5000, "wheat": 4500, "barley": 4000, "oats": 2500, "pea": 2000,
                                     "sunflower": 2500, "soy": 2200, "flax": 1500, "grain_legumes": 1800}.items()},
        traits=TRAITS,
    )
    base.update(over)
    return Context(**base)


EQUAL = {"yield": 25, "water": 25, "soil": 25, "risk": 25}


def test_hazard_helpers():
    assert is_hazard("heat35_jul_aug", 3) is True
    assert is_hazard("rootmoist_jja_z", -0.5) is False
    assert is_hazard("rootmoist_jja_z", None) is None
    hy = hazard_years(["heat35_jul_aug"], {"heat35_jul_aug": [0, 5]}, [2015, 2016])
    assert hy == {2015: [], 2016: ["heat35_jul_aug"]}
    assert median([None, 0, 2, 4]) == 3  # zeros / None ignored
    assert cv([1, 1, 1]) == 0
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3


def test_scores_are_bounded_and_explained():
    r = score_rotation(ctx(), ["maize", "wheat", "maize"], EQUAL)
    assert set(r["scores"]) == {"yield", "water", "soil", "risk"}
    assert all(0 <= v <= 100 for v in r["scores"].values())
    assert 0 <= r["total"] <= 100
    assert all(r["factors"][k] for k in r["scores"])  # every sub-score has factors
    assert len(r["years"]) == 3


def test_legume_rotation_scores_better_on_soil():
    mono = score_rotation(ctx(), ["maize", "wheat", "maize"], EQUAL)
    leg = score_rotation(ctx(), ["pea", "maize", "oats", "sunflower"], EQUAL)
    assert leg["scores"]["soil"] > mono["scores"]["soil"]


def test_cereal_after_legume_gets_yield_bonus():
    r = score_rotation(ctx(), ["pea", "maize", "wheat"], EQUAL)
    assert any("after pea" in e for e in r["years"][1]["effects"])


def test_repeat_and_interval_penalties():
    r = score_rotation(ctx(), ["maize", "maize", "wheat"], EQUAL)
    assert any("same crop" in e for e in r["years"][1]["effects"])
    pea3 = score_rotation(ctx(), ["pea", "wheat", "maize"], EQUAL)  # pea every 3 years < 4
    assert any("pea returns" in f["value"] for f in pea3["factors"]["soil"])
    pea4 = score_rotation(ctx(), ["pea", "wheat", "maize", "oats"], EQUAL)
    assert not any("pea returns" in f["value"] for f in pea4["factors"]["soil"])


def test_priorities_change_total():
    rot = ["pea", "maize", "oats", "sunflower"]
    soil_first = score_rotation(ctx(), rot, {"yield": 0, "water": 0, "soil": 1, "risk": 0})
    assert soil_first["total"] == soil_first["scores"]["soil"]


def test_risk_reflects_hazard_years():
    calm = ctx()
    calm.agro["values"]["heat35_jul_aug"] = [0] * 11
    a = score_rotation(calm, ["maize", "wheat", "maize"], EQUAL)["scores"]["risk"]
    b = score_rotation(ctx(), ["maize", "wheat", "maize"], EQUAL)["scores"]["risk"]
    assert a > b


def test_unknown_crop_rejected():
    with pytest.raises(ValueError):
        score_rotation(ctx(), ["maize", "banana", "wheat"], EQUAL)


def test_commune_has_lower_confidence():
    r = score_rotation(ctx(unit={"id": "AB-0001", "kind": "commune"}), ["maize", "wheat", "maize"], EQUAL)
    assert r["confidence"]["level"] == "low"


def test_forecast_learns_weather_effect_and_gates_on_skill():
    """Synthetic: yield drops 2 % per hot day -> model recovers it; pure noise -> no weather signal."""
    import random

    from app.scoring.forecast import forecast

    rnd = random.Random(1)
    years = list(range(2000, 2027))
    counties = {f"C{i}": f"County {i}" for i in range(8)}
    traits = {"crops": {"maize": {"sensitive": {"hazards": ["heat35_jul_aug"]}}}}
    meta = {"heat35_jul_aug": {"label": "Very hot days", "unit": "days"}}
    ins = {"years": list(range(2015, 2026)), "counties": {c: {"maize": {"area_ha": [1000.0] * 11, "production_t": [5000.0] * 11}} for c in counties}}

    def build(signal: bool):
        weather, yields = {}, {}
        for c in counties:
            heat = [rnd.uniform(0, 10) for _ in years]
            yields[c] = {"maize": [5000 * (1 - (0.02 * h if signal else 0) + rnd.gauss(0, 0.02 if signal else 0.15)) for h in heat[:-1]] + [None]}
            weather[c] = {"heat35_jul_aug": heat}
        inputs = {"years": years, "indicators": meta, "counties": weather, "yields": yields}
        return forecast("maize", counties, ins, inputs, traits)

    good = build(True)
    eff = good["model"]["predictors"][0]["effect_pct_per_unit"]
    assert -2.6 < eff < -1.4 and good["model"]["signal"] == "strong"
    f = good["counties"]["C0"]["forecast"]
    iv = f["intervals_kg_ha"]
    assert f["year"] == 2026 and iv["90"][0] <= iv["80"][0] <= iv["50"][0] <= f["yield_kg_ha"] <= iv["50"][1] <= iv["80"][1] <= iv["90"][1]
    assert 70 <= good["coverage_80_pct"] <= 90
    assert good["region"] is not None
    assert build(False)["model"]["signal"] == "none"
