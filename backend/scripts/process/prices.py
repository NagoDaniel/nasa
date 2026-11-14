"""INS TEMPO PPA102C farm-gate prices -> data/crops/prices.json (lei/t per crop, region, year).

Counties map to their development region (Alba, Mureș, Sibiu: Centru; Bihor, Cluj:
Nord-Vest; Arad, Hunedoara: Vest; Vâlcea: Sud-Vest Oltenia). Pea (only green pods in
the table), chickpea and flax have no farm-gate price here and are left out on purpose.
"""

from __future__ import annotations

import pandas as pd

from common import raw, write_json

PRODUCT = {"wheat": ["Grau"], "barley": ["Orz", "Orz - Orzoaica", "Orzoaica"], "oats": ["Ovaz"], "maize": ["Porumb boabe"],
           "sunflower": ["Floarea soarelui"], "soy": ["Soia"], "rapeseed": ["Rapita"]}
REGION = {"TOTAL": "RO", "Regiunea CENTRU": "Centru", "Regiunea NORD-VEST": "Nord-Vest", "Regiunea VEST": "Vest",
          "Regiunea SUD-VEST OLTENIA": "Sud-Vest Oltenia"}
COUNTY_REGION = {"AB": "Centru", "MS": "Centru", "SB": "Centru", "BH": "Nord-Vest", "CJ": "Nord-Vest",
                 "AR": "Vest", "HD": "Vest", "VL": "Sud-Vest Oltenia"}


def main() -> None:
    f = raw("crops/ins_tempo/PPA102C_prices.csv")
    if not f.exists():
        print("  no PPA102C_prices.csv (run scripts/download/prices.py), skipping")
        return
    df = pd.read_csv(f, sep=", ", engine="python")
    df.columns = ["product", "region", "period", "um", "value"]
    for c in ["product", "region", "period"]:
        df[c] = df[c].astype(str).str.strip()
    df["year"] = df["period"].str.replace("Anul ", "", regex=False).astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="coerce") * 1000  # lei/kg -> lei/t
    years = sorted(df["year"].unique().tolist())
    out: dict = {}
    for crop, names in PRODUCT.items():
        for reg, rid in REGION.items():
            for n in names:
                s = df[(df["product"] == n) & (df["region"] == reg)].set_index("year")["value"]
                vals = [None if y not in s.index or pd.isna(s[y]) else round(float(s[y])) for y in years]
                if any(v is not None for v in vals):
                    out.setdefault(crop, {})[rid] = vals
                    break
    print(f"  prices {years[0]}–{years[-1]} for {sorted(out)}; maize Centru {out['maize']['Centru'][-3:]} lei/t")
    write_json("crops/prices.json", {
        "source": "INS TEMPO PPA102C — average farm-gate prices of the main agricultural products, by development region",
        "unit": "lei/t", "years": years, "county_region": COUNTY_REGION,
        "missing": {"pea": "only green pea pods are priced", "chickpea": "not in the table", "flax": "not in the table"},
        "note": "Nominal prices (not inflation-adjusted). Prices received by farmers selling to processors / traders; contract prices can differ.",
        "crops": out,
    })


if __name__ == "__main__":
    main()
