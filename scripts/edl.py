"""Shared helpers: Earthdata token auth + CMR granule search + download."""
import json, os, pathlib, urllib.parse, urllib.request

TOKEN = pathlib.Path.home().joinpath(".earthdata_token").read_text().strip()
BBOX = "23.0,45.6,24.2,46.5"  # W,S,E,N  Alba Iulia region
START, END = "2021-11-01T00:00:00Z", "2026-10-31T23:59:59Z"

def cmr(short_name, version=None, temporal=True, page_size=2000, **extra):
    q = {"short_name": short_name, "bounding_box": BBOX, "page_size": page_size}
    if version: q["version"] = version
    if temporal: q["temporal"] = f"{START},{END}"
    q.update(extra)
    url = "https://cmr.earthdata.nasa.gov/search/granules.json?" + urllib.parse.urlencode(q)
    items = json.load(urllib.request.urlopen(url, timeout=120))["feed"]["entry"]
    return items

def data_urls(entry, suffixes=(".h5", ".hdf", ".nc4", ".nc", ".tif", ".zip")):
    return [l["href"] for l in entry.get("links", [])
            if l.get("rel", "").endswith("/data#") and l["href"].startswith("https")
            and l["href"].lower().endswith(suffixes)]

def download(url, dest, tries=5):
    import time
    dest = pathlib.Path(dest); dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0: return dest
    part = dest.with_name(dest.name + ".part")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
                while chunk := r.read(1 << 20): f.write(chunk)
            part.rename(dest); return dest
        except Exception as e:
            print("retry", i + 1, url[-50:], e, flush=True); time.sleep(5 * (i + 1))
    raise RuntimeError("download failed: " + url)
