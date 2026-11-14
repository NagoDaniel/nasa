"""Transparent rotation scoring (requirement 6).

Four sub-scores, 0–100 (higher = better), each with the factors that produced it:
  yield  – local yield level vs Romania (INS), rotation effects, soil pH fit
  water  – crop water need vs dry-year growing-season rain in this area
  soil   – legumes, crop diversity, winter cover, rotation intervals
  risk   – how often the crop's sensitive window was hit by hazards here (2015–2025,
           plus 2026 where NASA POWER has it)
           and how much the county yield swung (INS)
Total = priority-weighted mean of the four. Pure functions: all inputs are passed in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import i18n as I
from .hazards import HAZARDS, clean, crop_hazard_keys, cv, hazard_years, median, percentile

SUB = ("yield", "water", "soil", "risk")


@dataclass
class Factor:
    label: str
    value: str
    effect: str  # "+", "−" or "·"
    source: str
    assumption: str | None = None

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Context:
    unit: dict
    agro: dict  # {"years", "values": {indicator: [per year]}}
    soil: dict | None  # SoilGrids record for the unit
    ins_county: dict  # INS {crop: {area_ha, production_t, yield_kg_ha}}
    ins_ro: dict
    traits: dict  # crop_traits.json
    years: list[int] = field(default_factory=list)
    terrain: dict | None = None  # SRTM / WorldCover record (land/terrain.json), if the unit is covered


def _r(x: float | None, nd: int = 0) -> str:
    if x is None:
        return "n/a"
    return I.num(x, nd)


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def yield_series(ctx: Context, crop: str) -> tuple[list, list, str]:
    """County and Romania yield series; chickpea falls back to grain legumes."""
    key = crop if crop in ctx.ins_county else None
    note = I.t("ins_note")
    if crop == "chickpea" or key is None:
        key = "grain_legumes"
        note = I.t("ins_proxy_note")
    c = (ctx.ins_county.get(key) or {}).get("yield_kg_ha") or []
    r = (ctx.ins_ro.get(key) or {}).get("yield_kg_ha") or []
    return c, r, note


# ----------------------------------------------------------------------------- per crop
def crop_profile(ctx: Context, crop: str) -> dict[str, Any]:
    t = ctx.traits["crops"][crop]
    c, r, ins_note = yield_series(ctx, crop)
    med_c, med_r = median(c), median(r)
    ratio = (med_c / med_r) if med_c and med_r else None
    p10, p90 = percentile(clean(c), 0.1), percentile(clean(c), 0.9)

    precip = ctx.agro["values"].get("precip_apr_sep") or []
    supply_dry = percentile(precip, 0.2)
    supply_mean = (sum(clean(precip)) / len(clean(precip))) if clean(precip) else None
    need = sum(t["water_need_mm"]) / 2

    hk = crop_hazard_keys(t)
    hy = hazard_years(hk, ctx.agro["values"], ctx.agro["years"])
    valid_years = [y for y in hy if any(
        (ctx.agro["values"].get(k) or [None] * len(ctx.agro["years"]))[ctx.agro["years"].index(y)] is not None for k in hk)]
    bad_years = [y for y in valid_years if hy[y]]
    freq = len(bad_years) / len(valid_years) if valid_years else None

    ph = (ctx.soil or {}).get("phh2o", {}) or {}
    ph_med = ph.get("median")
    lo, hi = t["ph_opt"]
    ph_ok = None if ph_med is None else (lo <= ph_med <= hi)

    return {
        "crop": crop, "trait": t, "yield_median": med_c, "yield_ro_median": med_r, "yield_ratio": ratio,
        "yield_p10": p10, "yield_p90": p90, "yield_cv": cv(c), "ins_note": ins_note,
        "supply_dry": supply_dry, "supply_mean": supply_mean, "need": need,
        "hazard_keys": hk, "hazard_years": {y: hy[y] for y in bad_years}, "hazard_freq": freq,
        "n_years": len(valid_years), "ph_median": ph_med, "ph_ok": ph_ok,
    }


# ----------------------------------------------------------------------------- scoring
def score_rotation(ctx: Context, crops: list[str], priorities: dict[str, float], prev_crop: str | None = None) -> dict[str, Any]:
    """prev_crop: the crop grown the year before year 1 (field planner); default: the rotation repeats."""
    unknown = [c for c in crops if c not in ctx.traits["crops"]]
    if unknown:
        raise ValueError(f"unknown crops: {unknown}")
    A = ctx.traits["assumptions"]
    profiles = {c: crop_profile(ctx, c) for c in set(crops)}
    factors: dict[str, list[Factor]] = {k: [] for k in SUB}
    years_out = []

    # ---- yield + water + risk per year
    y_scores, w_scores, r_scores = [], [], []
    for i, crop in enumerate(crops):
        p = profiles[crop]
        t = p["trait"]
        prev = crops[i - 1] if i > 0 else (prev_crop or crops[-1])  # default: year 1 follows the last year
        mult = 1.0
        effects = []
        wrap = I.t("rot_wrap_last" if prev_crop else "rot_wrap_repeat") if i == 0 else ""
        if t["family"] == "cereal" and ctx.traits["crops"][prev]["legume"]:
            mult += A["legume_precrop_yield_bonus"]["value"]
            effects.append(I.t("rot_after_legume", p=I.pct(A["legume_precrop_yield_bonus"]["value"]), prev=I.crop(prev), wrap=wrap))
        if prev == crop:
            mult -= A["repeat_penalty"]["value"]
            effects.append(I.t("rot_repeat", p=I.pct(A["repeat_penalty"]["value"]), wrap=wrap))
        if p["ph_ok"] is False:
            mult -= 0.05
            effects.append(I.t("rot_ph"))
        base = 60 * p["yield_ratio"] if p["yield_ratio"] else 50
        ys = _clamp(base * mult)
        ws = _clamp(100 * min(1.0, (p["supply_dry"] or 0) / p["need"])) if p["supply_dry"] else 50
        freq = p["hazard_freq"]
        ycv = p["yield_cv"]
        rs = _clamp(100 * (1 - (0.6 * (freq if freq is not None else 0.5) + 0.4 * min(1.0, (ycv if ycv is not None else 0.2) / 0.4))))
        y_scores.append(ys)
        w_scores.append(ws)
        r_scores.append(rs)
        exp_lo = p["yield_p10"] * mult if p["yield_p10"] else None
        exp_hi = p["yield_p90"] * mult if p["yield_p90"] else None
        years_out.append({
            "year": i + 1, "crop": crop, "yield": round(ys), "water": round(ws), "risk": round(rs),
            "expected_yield_kg_ha": [round(exp_lo) if exp_lo else None, round(exp_hi) if exp_hi else None],
            "effects": effects,
        })

    seen = set()
    for crop in crops:
        if crop in seen:
            continue
        seen.add(crop)
        p = profiles[crop]
        t = p["trait"]
        cn = I.crop(crop)
        factors["yield"].append(Factor(
            I.t("f_yield_label", crop=cn),
            I.t("f_yield_value", c=_r(p["yield_median"]), r=_r(p["yield_ro_median"]), x=_r(p["yield_ratio"], 2)) if p["yield_ratio"] else I.t("f_no_stats"),
            "+" if (p["yield_ratio"] or 1) >= 1 else "−", p["ins_note"],
            I.t("f_yield_assume"),
        ))
        if p["ph_ok"] is not None:
            factors["yield"].append(Factor(
                I.t("f_ph_label", crop=cn), I.t("f_ph_value", ph=_r(p["ph_median"], 1), lo=_r(t["ph_opt"][0], 1), hi=_r(t["ph_opt"][1], 1)),
                "·" if p["ph_ok"] else "−", I.t("f_ph_source", ref=t["ph_ref"]),
                None if p["ph_ok"] else I.t("f_ph_assume"),
            ))
        factors["water"].append(Factor(
            I.t("f_water_label", crop=cn),
            I.t("f_water_value", lo=t["water_need_mm"][0], hi=t["water_need_mm"][1], dry=_r(p["supply_dry"]), avg=_r(p["supply_mean"])),
            "+" if (p["supply_dry"] or 0) >= p["need"] else "−",
            I.t("f_water_source", ref=I.L(t["water_ref"])),
            I.t("f_water_assume"),
        ))
        hz_txt = "; ".join(f"{y}: {', '.join(HAZARDS[k].text for k in ks)}" for y, ks in p["hazard_years"].items()) or I.t("f_none")
        factors["risk"].append(Factor(
            I.t("f_risk_label", crop=cn, stage=I.L(t["sensitive"]["stage"]), window=I.months(t["sensitive"]["window"])),
            I.t("f_risk_value", n=len(p["hazard_years"]), m=p["n_years"], list=hz_txt),
            "−" if p["hazard_years"] else "+",
            I.t("f_risk_source"),
            I.t("f_thresholds", list="; ".join(HAZARDS[k].text for k in p["hazard_keys"])) + " " + I.L(t["sensitive"]["quality"]),
        ))
        if p["yield_cv"] is not None:
            factors["risk"].append(Factor(
                I.t("f_cv_label", crop=cn),
                I.t("f_cv_value", cv=I.pct(p["yield_cv"])),
                "−" if p["yield_cv"] > 0.2 else "·", p["ins_note"],
                I.t("f_cv_assume"),
            ))

    # ---- soil health (rotation level)
    tr = ctx.traits["crops"]
    n = len(crops)
    legumes = sum(1 for c in crops if tr[c]["legume"])
    families = {tr[c]["family"] for c in crops}
    winter = sum(1 for c in crops if tr[c]["winter_cover"])
    leg_pts = 0 if legumes == 0 else (20 if legumes == 1 else 30)
    div_pts = {1: 0, 2: 15, 3: 25}.get(len(families), 30)
    win_pts = 20 * winter / n
    violations = []
    for c in dict.fromkeys(crops):
        gap = tr[c]["min_return_years"]
        pos = [i for i, x in enumerate(crops) if x == c]
        # cyclic distance to the next time the same crop is grown (rotation repeats)
        dists = [((pos[(k + 1) % len(pos)] - p) % n) or n for k, p in enumerate(pos)]
        if min(dists) < gap:
            violations.append(I.t("f_interval_bad", crop=I.crop(c), n=min(dists), gap=gap))
    int_pts = max(0, 20 - 10 * len(violations))
    soil_score = _clamp(leg_pts + div_pts + win_pts + int_pts)
    factors["soil"] += [
        Factor(I.t("f_legume_label"), I.t("f_of", a=legumes, b=n), "+" if legumes else "−", I.t("f_legume_source"),
               I.t("f_legume_assume")),
        Factor(I.t("f_families_label"), f"{len(families)}: {', '.join(I.family(f) for f in sorted(families))}", "+" if len(families) >= 3 else "·",
               I.t("f_traits"), I.t("f_families_assume")),
        Factor(I.t("f_winter_label"), I.t("f_winter_value", a=winter, b=n), "+" if winter else "−",
               I.t("f_traits"), I.t("f_winter_assume")),
        Factor(I.t("f_interval_label"), "; ".join(violations) or I.t("f_interval_ok"),
               "−" if violations else "+", I.t("f_interval_source"), I.t("f_interval_assume")),
    ]
    if ctx.soil and ctx.soil.get("soc"):
        factors["soil"].append(Factor(
            I.t("f_soc_label"), I.t("f_soc_value", v=_r(ctx.soil["soc"]["median"], 1), tex=I.texture(ctx.soil.get("texture", "")) or ""),
            "·", "ISRIC SoilGrids 2.0", I.t("f_context_only")))
    if ctx.terrain and ctx.terrain.get("cropland_slope_pct") is not None:
        bare = [c for c in dict.fromkeys(crops) if not tr[c]["winter_cover"]]
        factors["soil"].append(Factor(
            I.t("f_slope_label"),
            I.t("f_slope_value", m=_r(ctx.terrain["cropland_slope_pct"], 1), s=_r(ctx.terrain["cropland_steep_share_pct"], 1)),
            "·", I.t("f_slope_source"),
            I.t("f_slope_assume", bare=I.crops(bare) or I.t("f_none"))))

    sub = {
        "yield": sum(y_scores) / n,
        "water": sum(w_scores) / n,
        "soil": soil_score,
        "risk": sum(r_scores) / n,
    }
    w = {k: max(0.0, float(priorities.get(k, 0))) for k in SUB}
    wsum = sum(w.values()) or 1.0
    total = sum(sub[k] * w[k] for k in SUB) / wsum

    conf = "medium" if ctx.unit["kind"] == "county" else "low"
    conf_notes = [I.t("rot_conf_base")]
    if ctx.unit["kind"] == "commune":
        conf_notes.append(I.t("rot_conf_commune"))
    if "chickpea" in crops or "flax" in crops:
        conf = "low"
        conf_notes.append(I.t("rot_conf_sparse"))

    return {
        "crops": crops,
        "scores": {k: round(v) for k, v in sub.items()},
        "total": round(total),
        "weights": {k: round(w[k] / wsum, 3) for k in SUB},
        "years": years_out,
        "factors": {k: [f.as_dict() for f in v] for k, v in factors.items()},
        "confidence": {"level": conf, "notes": conf_notes},
    }
