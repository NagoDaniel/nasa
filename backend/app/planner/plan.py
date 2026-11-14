"""'Plan my field': answers + data -> a 3–4 year plan for one field (pure functions).

Steps
1. Allowed crops = considered − refused − what the farmer's machinery / nitrogen limit rules out.
2. Every sequence of allowed crops is checked (≤ 9⁴ = 6,561): rotation return gaps (also
   against what grew here before), "must grow" crops. Survivors are scored with the existing
   transparent rotation score (yield / water / soil / risk, farmer's weights), using the
   rotation effects learned from reports, the field's soil test, and year 1 following last
   year's real crop. Risk attitude and irrigation adjust the weights; a contract crop gets
   +CONTRACT_BONUS points. Best plan + 2 alternatives.
3. Per year: sowing window, maturity class, harvest, yield range for this field (county trend
   × the field's own level × previous-crop effect), tonnes, seed, nitrogen, water and hazard
   odds, and money when a price exists.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any

from ..scoring.rotation import Context, score_rotation
from . import climate as C
from .yields import planning_yield

CROPS = ["maize", "wheat", "barley", "oats", "pea", "chickpea", "sunflower", "soy", "flax"]
ROW_CROPS = {"maize", "sunflower", "soy"}
CONTRACT_BONUS = 5
RISK_WEIGHT = {"careful": 1.5, "balanced": 1.0, "bold": 0.5}


def allowed_crops(a: dict, traits: dict) -> tuple[list[str], list[str]]:
    why = []
    consider = [c for c in (a.get("consider") or CROPS) if c in traits["crops"]]
    out = [c for c in consider if c not in (a.get("avoid") or [])]
    if a.get("planter") is False:
        drop = [c for c in out if c in ROW_CROPS]
        if drop:
            why.append(f"No row-crop planter: {', '.join(drop)} left out.")
        out = [c for c in out if c not in ROW_CROPS]
    lim = a.get("n_limit")
    if lim is not None:
        drop = [c for c in out if sum(traits["crops"][c]["n_fert_kg_ha"]) / 2 > lim]
        if drop:
            why.append(f"Nitrogen limit {lim} kg/ha: {', '.join(drop)} need more and were left out.")
        out = [c for c in out if c not in drop]
    must = a.get("must_grow")
    if must and must not in out and must in traits["crops"]:
        out.append(must)
        why.append(f"{must} kept because you must grow it.")
    return out, why


def _gaps_ok(seq: tuple, history: dict[int, str], start: int, traits: dict) -> bool:
    last_seen = {}
    for y, c in sorted(history.items()):
        last_seen[c] = y
    for i, c in enumerate(seq):
        y = start + i
        gap = traits["crops"][c]["min_return_years"]
        if c in last_seen and y - last_seen[c] < gap:
            return False
        last_seen[c] = y
    # the plan must also be repeatable on its own
    n = len(seq)
    for c in set(seq):
        pos = [i for i, x in enumerate(seq) if x == c]
        dists = [((pos[(k + 1) % len(pos)] - p) % n) or n for k, p in enumerate(pos)]
        if min(dists) < traits["crops"][c]["min_return_years"]:
            return False
    return True


def search(ctx: Context, a: dict, crops: list[str], history: dict[int, str], start: int,
           autumn_open: bool = True) -> tuple[list[dict], int]:
    """autumn_open=False: the autumn sowing window before year 1 has passed, so year 1 cannot be a winter crop."""
    n_years = 4 if a.get("years", 4) == 4 else 3
    prio = dict(a.get("priorities") or {"yield": 25, "water": 25, "soil": 25, "risk": 25})
    prio["risk"] = prio.get("risk", 25) * RISK_WEIGHT.get(a.get("risk", "balanced"), 1.0)
    if a.get("irrigation") == "yes":
        prio["water"] = 0  # water is not the limiting factor on an irrigated field
    must, must_min = a.get("must_grow"), max(1, int(a.get("must_min") or 1))
    prev = history.get(start - 1)
    scored, checked = [], 0
    for seq in itertools.product(crops, repeat=n_years):
        if must and seq.count(must) < must_min:
            continue
        if not autumn_open and ctx.traits["crops"][seq[0]]["planner"]["sow"] == "winter":
            continue
        if not _gaps_ok(seq, history, start, ctx.traits):
            continue
        checked += 1
        r = score_rotation(ctx, list(seq), prio, prev_crop=prev)
        total = r["total"] + (CONTRACT_BONUS if a.get("contract_crop") in seq else 0)
        scored.append({"crops": list(seq), "score": total, "rotation": r})
    scored.sort(key=lambda s: -s["score"])
    picks: list[dict] = []
    for s in scored:  # best + alternatives that differ in which crops they use
        if all(set(s["crops"]) != set(p["crops"]) for p in picks):
            picks.append(s)
        if len(picks) == 3:
            break
    return picks, checked


def _price(crop: str, county: str, a: dict, prices: dict) -> dict | None:
    own = (a.get("prices") or {}).get(crop)
    if own:
        return {"lei_t": float(own), "source": "your price"}
    reg = prices["county_region"].get(county)
    s = ((prices["crops"].get(crop) or {}).get(reg) or (prices["crops"].get(crop) or {}).get("RO") or [])
    recent = [v for v in s[-3:] if v]
    if not recent:
        return None
    recent.sort()
    return {"lei_t": recent[len(recent) // 2], "source": f"INS farm-gate price, {reg or 'Romania'}, median {prices['years'][-3]}–{prices['years'][-1]}"}


def year_detail(crop: str, year: int, prev: str | None, county: str, area: float, a: dict, d: dict, level: dict,
                effects: dict) -> dict[str, Any]:
    traits, inputs, ins = d["traits"], d["inputs"], d["ins"]
    t = traits["crops"][crop]
    clim = inputs["climate"]["counties"][county]
    w = inputs["counties"][county]
    years = inputs["years"]
    upto = years[-1]
    sow = C.sowing(crop, t, clim, years)
    want = (a.get("maturity") or {}).get(crop, "suggest")
    suggested, options = (C.suggest_maturity(crop, t, clim, years, sow) if t["planner"].get("maturity") else (None, []))
    cls = suggested if want in (None, "suggest") else want
    mat = next((m for m in options if m["class"] == cls), None)

    mult, why = level["factor"], []
    if level["n"]:
        why.append(f"your field {level['pct']:+.0f} % vs county ({level['n']} season{'s' if level['n'] != 1 else ''})")
    if prev and t["family"] == "cereal" and traits["crops"][prev]["legume"]:
        mult *= 1 + effects["legume_precrop_yield_bonus"]["used"]
        why.append(f"+{effects['legume_precrop_yield_bonus']['used']:.0%} after {prev}")
    if prev == crop:
        mult *= 1 - effects["repeat_penalty"]["used"]
        why.append(f"−{effects['repeat_penalty']['used']:.0%} same crop as the year before")
    ph = (d.get("soil") or {}).get("ph")
    if ph is not None and not (t["ph_opt"][0] <= ph <= t["ph_opt"][1]):
        mult *= 0.95
        why.append(f"−5 % soil pH {ph} outside {t['ph_opt'][0]}–{t['ph_opt'][1]}")
    py = planning_yield(crop, county, inputs, ins, year)
    yld = None
    if py:
        rng = {k: [max(0.0, v[0] * mult), v[1] * mult] for k, v in py["range_kg_ha"].items()}
        yld = {"t_ha": py["normal_kg_ha"] * mult / 1000, "range_t_ha": {k: [v[0] / 1000, v[1] / 1000] for k, v in rng.items()},
               "tonnes": py["normal_kg_ha"] * mult * area / 1000, "range_t": {k: [v[0] * area / 1000, v[1] * area / 1000] for k, v in rng.items()},
               "basis": py["basis"], "confidence": py["confidence"], "proxy": py["proxy"], "adjustments": why}
    seed = t["planner"]["seed_rate_kg_ha"]
    n_mid = sum(t["n_fert_kg_ha"]) / 2
    price = _price(crop, county, a, d["prices"])
    money = None
    if price and yld:
        cost = (a.get("costs") or {}).get(crop)
        rev = {k: [v[0] * price["lei_t"], v[1] * price["lei_t"]] for k, v in yld["range_t"].items()}
        money = {"price_lei_t": price["lei_t"], "price_source": price["source"], "revenue_lei": yld["tonnes"] * price["lei_t"],
                 "revenue_range_lei": rev, "cost_lei_ha": cost,
                 "margin_lei": None if cost is None else yld["tonnes"] * price["lei_t"] - cost * area,
                 "margin_range_lei": None if cost is None else {k: [v[0] - cost * area, v[1] - cost * area] for k, v in rev.items()}}
    water = C.water_odds(t, w, years, upto)
    return {
        "year": year, "crop": crop, "previous": prev,
        "sowing": sow if sow["kind"] == "winter" else {k: v for k, v in sow.items() if k != "per_year"},
        "maturity": mat, "maturity_options": options, "maturity_suggested": suggested, "maturity_chosen": cls,
        "harvest": (mat["harvest"] if mat else t["planner"].get("harvest_window") or t["harvest"]),
        "yield": yld,
        "seed": {"kg_ha": seed, "kg": [seed[0] * area, seed[1] * area]},
        "nitrogen": {"kg_ha": 0 if t["legume"] else n_mid, "kg": 0 if t["legume"] else n_mid * area, "legume": t["legume"],
                     "fixes_kg_ha": t.get("n_fixation_kg_ha"), "over_limit": a.get("n_limit") is not None and n_mid > a["n_limit"]},
        "water": {**water, "irrigated": a.get("irrigation") in ("yes", "partly")},
        "hazards": C.hazard_odds(crop, t, w, years, upto),
        "money": money,
        "quality_note": t["sensitive"]["quality"],
    }


def build_plan(field: dict, a: dict, d: dict, level: dict, effects: dict, start: int, autumn_open: bool = True) -> dict[str, Any]:
    """d: traits, inputs (forecast_inputs), ins, prices, unit, agro, soil (SoilGrids values), terrain."""
    county = field["county"]
    area = field["area_ha"]
    traits = copy.deepcopy(d["traits"])
    for k in ("legume_precrop_yield_bonus", "repeat_penalty"):
        traits["assumptions"][k]["value"] = effects[k]["used"]
    soil = copy.deepcopy(d.get("soil")) or {}
    st = a.get("soil_test") or {}
    if st.get("ph") is not None:
        soil["phh2o"] = {**(soil.get("phh2o") or {}), "median": st["ph"]}
    if st.get("soc_g_kg") is not None:
        soil["soc"] = {**(soil.get("soc") or {}), "median": st["soc_g_kg"]}
    if st.get("texture"):
        soil["texture"] = st["texture"]
    ctx = Context(unit=d["unit"], agro=d["agro"], soil=soil, ins_county=d["ins"]["counties"].get(county, {}),
                  ins_ro=d["ins"]["counties"].get("RO", {}), traits=traits, terrain=d.get("terrain"))
    history = {int(h["year"]): h["crop"] for h in (a.get("history") or []) if h.get("crop") in traits["crops"]}
    crops, notes = allowed_crops(a, traits)
    if not crops:
        return {"error": "No crop is left after your answers (considered / refused / machinery / nitrogen). Allow more crops."}
    picks, checked = search(ctx, a, crops, history, start, autumn_open)
    if not autumn_open:
        notes.append(f"The autumn sowing window for the {start} harvest has passed, so year 1 is a spring crop.")
    if not picks:
        return {"error": "No rotation fits: the return gaps after what grew here and your 'must grow' crop rule out every sequence. "
                         "Allow more crops or fewer years of the must-grow crop."}
    dd = {**d, "traits": traits, "soil": {"ph": soil.get("phh2o", {}).get("median")}}
    plans = []
    for p in picks:
        prev = history.get(start - 1)
        yrs = []
        for i, c in enumerate(p["crops"]):
            yrs.append(year_detail(c, start + i, prev, county, area, a, dd, level, effects))
            prev = c
        tot_rev = [y["money"]["revenue_lei"] for y in yrs if y["money"]]
        plans.append({
            "crops": p["crops"], "score": p["score"], "scores": p["rotation"]["scores"], "factors": p["rotation"]["factors"],
            "contract_bonus": CONTRACT_BONUS if a.get("contract_crop") in p["crops"] else 0,
            "years": yrs,
            "totals": {
                "seed_kg": sum(sum(y["seed"]["kg"]) / 2 for y in yrs), "nitrogen_kg": sum(y["nitrogen"]["kg"] for y in yrs),
                "revenue_lei": sum(tot_rev) if len(tot_rev) == len(yrs) else None,
            },
        })
    return {
        "start_year": start, "county": county, "area_ha": area, "allowed": crops, "notes": notes,
        "sequences_checked": checked, "plans": plans,
        "weights_used": {"risk_attitude": a.get("risk", "balanced"), "irrigated": a.get("irrigation") == "yes",
                         "contract_crop": a.get("contract_crop"), "contract_bonus": CONTRACT_BONUS},
    }
