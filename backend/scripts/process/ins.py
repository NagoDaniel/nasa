"""INS TEMPO AGR108A/109A/110A -> area, production, yield per county, crop and year."""

from __future__ import annotations

import json

import pandas as pd

from common import YEARS, raw, write_json

COUNTY = {"Alba": "AB", "Arad": "AR", "Bihor": "BH", "Cluj": "CJ", "Hunedoara": "HD",
          "Mures": "MS", "Sibiu": "SB", "Valcea": "VL", "TOTAL": "RO"}
# crop id -> INS name ("Principalele culturi")
CROPS = {
    "maize": "Porumb boabe",
    "barley": "Orz si orzoaica",
    "oats": "Ovaz",
    "pea": "Mazare boabe",
    "flax": "In pentru ulei",
    "sunflower": "Floarea soarelui",
    "wheat": "Grau comun",
    "soy": "Soia boabe",
    "rapeseed": "Rapita",
    "grain_legumes": "Leguminoase pentru boabe",
}
TABLES = {"AGR108A": "area_ha", "AGR109A": "production_t", "AGR110A": "yield_kg_ha"}


def read(code: str) -> pd.DataFrame:
    df = pd.read_csv(raw(f"crops/ins_tempo/{code}_AOI_2015plus.csv"), sep=", ", engine="python")
    df.columns = ["crop", "ownership", "area", "year", "um", "value"]
    for c in ["crop", "ownership", "area", "year"]:
        df[c] = df[c].astype(str).str.strip()
    df = df[df["ownership"] == "Total"]
    df["year"] = df["year"].str.replace("Anul ", "", regex=False).astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def main() -> None:
    out: dict = {c: {} for c in COUNTY.values()}
    updated = {}
    for code, field in TABLES.items():
        df = read(code)
        meta = json.loads(raw(f"crops/ins_tempo/{code}_metadata.json").read_text())
        updated[code] = meta.get("ultimaActualizare")
        for crop, ins_name in CROPS.items():
            sub = df[df["crop"] == ins_name]
            for area, code2 in COUNTY.items():
                s = sub[sub["area"] == area].set_index("year")["value"]
                vals = [None if y not in s.index or pd.isna(s[y]) else float(s[y]) for y in YEARS]
                out[code2].setdefault(crop, {})[field] = vals
    # Where INS has no yield table for a crop (e.g. grain legumes), derive it as production / area.
    derived = []
    for code2, crops in out.items():
        for crop, rec in crops.items():
            y = rec.get("yield_kg_ha") or []
            if all(v is None for v in y):
                a, p = rec.get("area_ha") or [], rec.get("production_t") or []
                rec["yield_kg_ha"] = [round(pp / aa * 1000) if aa and pp else None for aa, pp in zip(a, p)]
                rec["yield_derived"] = True
                derived.append(f"{code2}/{crop}")
    if derived:
        print(f"  derived yield = production / area for {len(derived)} series (e.g. {derived[0]})")
    alba_maize = out["AB"]["maize"]["yield_kg_ha"]
    print(f"  check: Alba maize yield 2018={alba_maize[YEARS.index(2018)]}, 2025={alba_maize[YEARS.index(2025)]}")
    write_json(
        "crops/ins_stats.json",
        {
            "source": "INS TEMPO Online (Romanian National Institute of Statistics): AGR108A area, AGR109A production, AGR110A average yield",
            "last_updated": updated,
            "years": YEARS,
            "fields": {"area_ha": "Cultivated area (ha)", "production_t": "Production (t)", "yield_kg_ha": "Average yield (kg/ha)"},
            "crops": {k: {"ins_name": v} for k, v in CROPS.items()},
            "not_available": {"chickpea": "INS does not report chickpea separately (it is inside 'grain legumes')."},
            "confidence": {
                "county": "high",
                "commune": "n/a",
                "note": "Official statistics, county level only. The latest year may be provisional. Commune views show their county's figures.",
            },
            "counties": out,
        },
    )


if __name__ == "__main__":
    main()
