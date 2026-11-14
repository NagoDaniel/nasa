"""Index of the analysis units (8 AOI counties + their communes) for the API."""

from __future__ import annotations

from pyproj import Geod

from common import AOI, load_units, write_json

GEOD = Geod(ellps="WGS84")


def main() -> None:
    units = []
    for u in load_units():
        area = abs(GEOD.geometry_area_perimeter(u.geom)[0]) / 1e6
        c = u.geom.representative_point()
        units.append({"id": u.id, "kind": u.kind, "name": u.name, "county": u.county,
                      "area_km2": round(area, 1), "point": [round(c.x, 4), round(c.y, 4)]})
    write_json("units.json", {"aoi": AOI, "units": units})
    print(f"  {sum(u['kind'] == 'county' for u in units)} counties, {sum(u['kind'] == 'commune' for u in units)} communes")


if __name__ == "__main__":
    main()
