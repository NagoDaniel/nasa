"""NASA POWER daily data for Alba Iulia region (no auth needed)."""
import json, urllib.request, pathlib
out = pathlib.Path("data/power"); out.mkdir(parents=True, exist_ok=True)
params = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN,GWETROOT,GWETTOP,EVLAND"
# 3x3 grid points covering ~45.6-46.5N, 23.0-24.2E
pts = [(lat, lon) for lat in (45.7, 46.07, 46.4) for lon in (23.1, 23.57, 24.1)]
for lat, lon in pts:
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?"
           f"parameters={params}&community=AG&longitude={lon}&latitude={lat}"
           "&start=20211101&end=20261031&format=JSON")
    f = out / f"power_{lat}_{lon}.json"
    with urllib.request.urlopen(url, timeout=120) as r:
        f.write_bytes(r.read())
    print(f, f.stat().st_size)
