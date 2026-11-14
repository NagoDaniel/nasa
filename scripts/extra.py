import sys, pathlib; sys.path.insert(0, "scripts")
import edl
JOBS = [("MOD11A2","061","modis_lst",True,(".hdf",)),
        ("MOD16A2GF","061","modis_et",True,(".hdf",)),
        ("TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",None,"grace_tws",False,(".nc",))]
for sn, ver, folder, temporal, suf in JOBS:
    for e in edl.cmr(sn, ver, temporal=temporal, **({} if ver else {"bounding_box": None} and {})):
        for u in edl.data_urls(e, suffixes=suf):
            p = edl.download(u, pathlib.Path("data")/folder/u.rsplit("/",1)[1])
            print(p, p.stat().st_size, flush=True)
print("EXTRADONE", flush=True)
