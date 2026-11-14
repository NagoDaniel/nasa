import sys, os, re, requests, time
from concurrent.futures import ThreadPoolExecutor
jobs=[]
D = os.path.expanduser(sys.argv[1]) + '/climate_scenarios/nex_gddp_cmip6'
B = 'https://ds.nccs.nasa.gov/thredds'
P = 'AMES/NEX/GDDP-CMIP6'
models = {'GFDL-ESM4':'r1i1p1f1', 'MPI-ESM1-2-HR':'r1i1p1f1', 'EC-Earth3':'r1i1p1f1'}
vars_ = ['tas','tasmax','tasmin','pr','hurs']
runs = {'historical': range(1995, 2015), 'ssp245': range(2025, 2061), 'ssp585': range(2025, 2061)}
for m, mem in models.items():
    for ssp, yrs in runs.items():
        for v in vars_:
            cat = requests.get(f'{B}/catalog/{P}/{m}/{ssp}/{mem}/{v}/catalog.xml', timeout=60).text
            names = re.findall(r'name="([^"]+\.nc)"', cat)
            if not names: print('nocat', m, ssp, v, flush=True); continue
            od = f'{D}/{m}/{ssp}/{v}'; os.makedirs(od, exist_ok=True)
            for y in yrs:
                cand = sorted([n for n in names if f'_{y}' in n and n.endswith('.nc')], key=lambda n: ('v2.0' not in n, 'v1.1' not in n))
                if not cand: print('noyear', m, ssp, v, y, flush=True); continue
                f = f'{od}/{v}_{m}_{ssp}_{y}_AOI.nc'
                if os.path.exists(f) and os.path.getsize(f) > 50000: continue
                u = f'{B}/ncss/grid/{P}/{m}/{ssp}/{mem}/{v}/{cand[0]}'
                jobs.append((u, v, f))
def fetch(job):
                u, v, f = job
                for a in range(4):
                    try:
                        r = requests.get(u, params=dict(var=v, north=47.75, south=44.25, west=20.5, east=25.5, horizStride=1, temporal='all', accept='netcdf4'), timeout=300)
                        if r.ok: open(f,'wb').write(r.content); print('ok', f, len(r.content), flush=True); break
                        print('err', r.status_code, u, flush=True)
                    except Exception as e: print('exc', e, flush=True)
                    time.sleep(5)

with ThreadPoolExecutor(8) as ex: list(ex.map(fetch, jobs))
print('DONE', flush=True)
