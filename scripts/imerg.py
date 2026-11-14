import sys, pathlib; sys.path.insert(0, "scripts")
import edl
for e in edl.cmr("GPM_3IMERGM", "07"):
    for u in edl.data_urls(e, suffixes=(".hdf5",)):
        p = edl.download(u, pathlib.Path("data/imerg_monthly") / u.rsplit("/", 1)[1])
        print(p, p.stat().st_size, flush=True)
