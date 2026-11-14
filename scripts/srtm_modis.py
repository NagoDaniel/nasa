import sys, pathlib; sys.path.insert(0, "scripts")
import edl
for sn, ver, folder, temporal in [("SRTMGL1", "003", "srtm", False), ("MOD13A3", "061", "modis_ndvi", True)]:
    entries = edl.cmr(sn, ver, temporal=temporal)
    for e in entries:
        for u in edl.data_urls(e):
            p = edl.download(u, pathlib.Path("data") / folder / u.rsplit("/", 1)[1])
            print(p, p.stat().st_size, flush=True)
