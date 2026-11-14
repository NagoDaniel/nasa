import sys, datetime as dt; sys.path.insert(0, "scripts")
import smap_harmony as sh
d = dt.date(2021, 11, 1)
while d < dt.date(2026, 11, 1):
    n = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    try: sh.run(f"{d}T00:00:00Z", f"{n}T00:00:00Z", d.strftime("%Y-%m"))
    except Exception as e: print("ERR", d, e, flush=True)
    d = n
print("ALLDONE", flush=True)
