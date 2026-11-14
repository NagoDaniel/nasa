"""SMAP L3 9km daily soil moisture, spatially subset to Alba Iulia region via Harmony."""
import sys, json, time, urllib.request, urllib.parse, pathlib
sys.path.insert(0, "scripts"); import edl
CID = "C2938664763-NSIDC_CPRD"
def call(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + edl.TOKEN}), timeout=300)
def run(t0, t1, out):
    q = urllib.parse.urlencode([("subset","lat(45.6:46.5)"),("subset","lon(23.0:24.2)"),
        ("subset",f'time("{t0}":"{t1}")'),("format","application/x-netcdf4")])
    j = json.load(call(f"https://harmony.earthdata.nasa.gov/{CID}/ogc-api-coverages/1.0.0/collections/all/coverage/rangeset?{q}"))
    job = next(l["href"] for l in j["links"] if l.get("rel") == "self")
    while j["status"] in ("running", "accepted"):
        time.sleep(10); j = json.load(call(job)); print(out, j["status"], j.get("progress"), flush=True)
    if j["status"] not in ("successful", "complete_with_errors"): print("FAIL", j.get("message")); return
    for i, l in enumerate(x for x in j["links"] if x.get("rel") == "data"):
        edl.download(l["href"], pathlib.Path("data/smap")/f"{out}_{i}_{l['href'].rsplit('/',1)[1].split('?')[0]}")
if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
