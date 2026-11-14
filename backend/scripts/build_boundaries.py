"""Build the Romania boundary layers used by the map (one-off / re-runnable).

Sources
  * geoBoundaries gbOpen ROU ADM2 (communes / UAT, from ANCPI cadastre, CC BY 4.0)
  * geoBoundaries gbOpen ROU ADM1 (counties, CC BY 4.0) — only used to assign
    each commune to its county; county shapes are dissolved from the communes
    so county, region and commune borders line up exactly.
  * OpenStreetMap (ODbL) admin_level=8 (UAT) names via Overpass — proper Romanian
    commune names with diacritics (optional; falls back to title-case).

Outputs (backend/data/geo/*.geojson.json):
  counties, regions, communes (Alba + neighbours), outline, mask, labels

Run:  uv run --group scripts python scripts/build_boundaries.py
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import requests
import shapely
from shapely.geometry import Point, box, mapping
from shapely.ops import polylabel

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "geo"
CACHE = ROOT / ".cache" / "boundaries"

GB_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ROU/{lvl}/geoBoundaries-ROU-{lvl}.geojson"
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = {"User-Agent": "space2feed-hackathon-boundary-builder/0.1"}

# code: (official name, development region, NUTS-2)
COUNTIES: dict[str, tuple[str, str, str]] = {
    "AB": ("Alba", "Centru", "RO12"),
    "AR": ("Arad", "Vest", "RO42"),
    "AG": ("Argeș", "Sud-Muntenia", "RO31"),
    "BC": ("Bacău", "Nord-Est", "RO21"),
    "BH": ("Bihor", "Nord-Vest", "RO11"),
    "BN": ("Bistrița-Năsăud", "Nord-Vest", "RO11"),
    "BT": ("Botoșani", "Nord-Est", "RO21"),
    "BV": ("Brașov", "Centru", "RO12"),
    "BR": ("Brăila", "Sud-Est", "RO22"),
    "B": ("București", "București-Ilfov", "RO32"),
    "BZ": ("Buzău", "Sud-Est", "RO22"),
    "CS": ("Caraș-Severin", "Vest", "RO42"),
    "CL": ("Călărași", "Sud-Muntenia", "RO31"),
    "CJ": ("Cluj", "Nord-Vest", "RO11"),
    "CT": ("Constanța", "Sud-Est", "RO22"),
    "CV": ("Covasna", "Centru", "RO12"),
    "DB": ("Dâmbovița", "Sud-Muntenia", "RO31"),
    "DJ": ("Dolj", "Sud-Vest Oltenia", "RO41"),
    "GL": ("Galați", "Sud-Est", "RO22"),
    "GR": ("Giurgiu", "Sud-Muntenia", "RO31"),
    "GJ": ("Gorj", "Sud-Vest Oltenia", "RO41"),
    "HR": ("Harghita", "Centru", "RO12"),
    "HD": ("Hunedoara", "Vest", "RO42"),
    "IL": ("Ialomița", "Sud-Muntenia", "RO31"),
    "IS": ("Iași", "Nord-Est", "RO21"),
    "IF": ("Ilfov", "București-Ilfov", "RO32"),
    "MM": ("Maramureș", "Nord-Vest", "RO11"),
    "MH": ("Mehedinți", "Sud-Vest Oltenia", "RO41"),
    "MS": ("Mureș", "Centru", "RO12"),
    "NT": ("Neamț", "Nord-Est", "RO21"),
    "OT": ("Olt", "Sud-Vest Oltenia", "RO41"),
    "PH": ("Prahova", "Sud-Muntenia", "RO31"),
    "SM": ("Satu Mare", "Nord-Vest", "RO11"),
    "SJ": ("Sălaj", "Nord-Vest", "RO11"),
    "SB": ("Sibiu", "Centru", "RO12"),
    "SV": ("Suceava", "Nord-Est", "RO21"),
    "TR": ("Teleorman", "Sud-Muntenia", "RO31"),
    "TM": ("Timiș", "Vest", "RO42"),
    "TL": ("Tulcea", "Sud-Est", "RO22"),
    "VS": ("Vaslui", "Nord-Est", "RO21"),
    "VL": ("Vâlcea", "Sud-Vest Oltenia", "RO41"),
    "VN": ("Vrancea", "Sud-Est", "RO22"),
}
FOCUS = ["AB", "AR", "BH", "CJ", "HD", "MS", "SB", "VL"]  # Alba + neighbours

SIMPLIFY_DEG = 0.0003  # ≈ 25-30 m; topology kept via coverage simplification
PRECISION = 5  # ≈ 1 m


def fetch(url: str, dest: Path, **kw) -> Path:
    if not dest.exists():
        print(f"  downloading {url}")
        r = requests.get(url, headers=UA, timeout=600, **kw)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def fold(s: str) -> str:
    s = s.replace("ş", "ș").replace("ţ", "ț").replace("Ş", "Ș").replace("Ţ", "Ț")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for prefix in ("municipiul ", "orasul ", "oras ", "comuna "):
        if s.lower().startswith(prefix):
            s = s[len(prefix):]
    return "".join(c for c in s.upper() if c.isalnum())


def osm_commune_names() -> list[tuple[Point, str]]:
    dest = CACHE / "osm_admin8.json"
    if not dest.exists():
        q = (
            '[out:json][timeout:240];area["ISO3166-1"="RO"][admin_level=2]->.ro;'
            'rel(area.ro)["boundary"="administrative"]["admin_level"="8"];out tags center;'
        )
        for url in OVERPASS:
            try:
                print(f"  querying {url}")
                r = requests.post(url, data={"data": q}, headers=UA, timeout=300)
                r.raise_for_status()
                dest.write_bytes(r.content)
                break
            except Exception as e:  # noqa: BLE001
                print(f"    failed: {e}")
        else:
            print("  ! OSM names unavailable, falling back to title-case names")
            return []
    data = json.loads(dest.read_text())
    out = []
    for el in data.get("elements", []):
        c, name = el.get("center"), el.get("tags", {}).get("name")
        if c and name:
            out.append((Point(c["lon"], c["lat"]), name))
    return out


_SMALL = {"de", "din", "pe", "sub", "la", "lui", "cu", "si"}


def nice_case(name: str) -> str:
    def word(w: str, i: int) -> str:
        return w.lower() if i and w.lower() in _SMALL else w.capitalize()

    return "-".join(" ".join(word(w, i) for i, w in enumerate(part.split(" "))) for part in name.split("-"))


def rounded(geom):
    return shapely.set_precision(geom, 10 ** -PRECISION)


def write(name: str, gdf_or_fc) -> None:
    path = OUT / f"{name}.geojson.json"
    if isinstance(gdf_or_fc, gpd.GeoDataFrame):
        fc = json.loads(gdf_or_fc.to_json(drop_id=True, to_wgs84=True))
    else:
        fc = gdf_or_fc
    path.write_text(json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size / 1e6:.2f} MB, {len(fc['features'])} features)")


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    print("1/6 loading sources")
    adm1 = gpd.read_file(fetch(GB_URL.format(lvl="ADM1"), CACHE / "ADM1.geojson")).to_crs(4326)
    adm2 = gpd.read_file(fetch(GB_URL.format(lvl="ADM2"), CACHE / "ADM2.geojson")).to_crs(4326)
    adm1["code"] = adm1["shapeISO"].str.replace("RO-", "", regex=False)
    unknown = set(adm1["code"]) - set(COUNTIES)
    if unknown:
        sys.exit(f"Unknown county codes in ADM1: {unknown}")

    print("2/6 assigning communes to counties")
    adm2["geometry"] = adm2.geometry.make_valid()
    pts = adm2.copy()
    pts["geometry"] = adm2.geometry.representative_point()
    joined = gpd.sjoin(pts, adm1[["code", "geometry"]], how="left", predicate="within")
    joined = joined[~joined.index.duplicated()]
    adm2["county"] = joined["code"]
    missing = adm2["county"].isna()
    if missing.any():  # coastline / border slivers: nearest county
        near = gpd.sjoin_nearest(pts[missing], adm1[["code", "geometry"]], how="left")
        adm2.loc[missing, "county"] = near[~near.index.duplicated()]["code"]
    # Merge multi-row UATs (same name, same county) into one feature
    adm2 = adm2.dissolve(by=["county", "shapeName"], as_index=False, aggfunc="first")
    print(f"  {len(adm2)} UATs")

    print("3/6 resolving commune names (diacritics)")
    osm = osm_commune_names()
    osm_gdf = gpd.GeoDataFrame({"osm_name": [n for _, n in osm]}, geometry=[p for p, _ in osm], crs=4326) if osm else None
    names = {}
    if osm_gdf is not None:
        hit = gpd.sjoin(osm_gdf, adm2[["shapeName", "geometry"]], how="inner", predicate="within")
        for idx, grp in hit.groupby("index_right"):
            target = fold(adm2.at[idx, "shapeName"])
            exact = [n for n in grp["osm_name"] if fold(n) == target]
            if exact:
                names[idx] = exact[0]
    matched = len(names)
    adm2["name"] = [names.get(i, nice_case(n)) for i, n in zip(adm2.index, adm2["shapeName"])]
    print(f"  matched {matched}/{len(adm2)} names to OSM")

    adm2["region"] = adm2["county"].map(lambda c: COUNTIES[c][1])
    adm2 = adm2.sort_values(["county", "name"]).reset_index(drop=True)
    adm2["id"] = [f"{c}-{i:04d}" for i, c in enumerate(adm2["county"])]

    print("4/6 coverage-simplifying (shared edges stay shared)")
    simple = adm2.copy()
    simple["geometry"] = shapely.coverage_simplify(adm2.geometry.values, SIMPLIFY_DEG)
    simple["geometry"] = rounded(simple.geometry.make_valid())

    print("5/6 dissolving counties, regions, outline")
    counties = simple.dissolve(by="county", as_index=False)[["county", "geometry"]].rename(columns={"county": "code"})
    counties["name"] = counties["code"].map(lambda c: COUNTIES[c][0])
    counties["region"] = counties["code"].map(lambda c: COUNTIES[c][1])
    counties["nuts2"] = counties["code"].map(lambda c: COUNTIES[c][2])
    counties["geometry"] = rounded(counties.geometry.buffer(0))
    regions = counties.dissolve(by="region", as_index=False)[["region", "nuts2", "geometry"]].rename(columns={"region": "name"})
    regions["geometry"] = rounded(regions.geometry.buffer(0))
    outline_geom = rounded(shapely.union_all(counties.geometry.values).buffer(0))

    communes = simple[simple["county"].isin(FOCUS)][["id", "name", "county", "region", "geometry"]]
    communes["county_name"] = communes["county"].map(lambda c: COUNTIES[c][0])

    print("6/6 labels + mask, writing")
    labels = []
    for kind, gdf, name_col in (("region", regions, "name"), ("county", counties, "name"), ("commune", communes, "name")):
        for _, row in gdf.iterrows():
            g = row.geometry
            part = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
            p = polylabel(part, tolerance=0.002 if kind != "commune" else 0.0005)
            props = {"kind": kind, "name": row[name_col]}
            if kind == "county":
                props["code"] = row["code"]
            labels.append({"type": "Feature", "properties": props, "geometry": mapping(rounded(p))})

    mask = box(-180, -85, 180, 85).difference(outline_geom)

    write("counties", counties[["code", "name", "region", "nuts2", "geometry"]])
    write("regions", regions)
    write("communes", communes)
    write("outline", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "România"}, "geometry": mapping(outline_geom)}]})
    write("mask", {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": mapping(rounded(mask))}]})
    write("labels", {"type": "FeatureCollection", "features": labels})

    print(f"\ncounties={len(counties)} regions={len(regions)} communes(focus)={len(communes)}")


if __name__ == "__main__":
    main()
