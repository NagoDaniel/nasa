# usage: power.py <raw dir> [START END SUBDIR]   default 20150101 20251231 daily_grid
# extra periods go to their own folder (e.g. 20000101 20141231 daily_grid_2000_2014); the
# processing step concatenates all daily_grid* folders per cell.
import sys, os, time, requests
START, END, SUB = (sys.argv[2:5] if len(sys.argv) >= 5 else ('20150101', '20251231', 'daily_grid'))
D = os.path.expanduser(sys.argv[1]) + f'/nasa_power/{SUB}'; os.makedirs(D, exist_ok=True)
P = ('T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS2M,GWETTOP,GWETROOT,GWETPROF,EVPTRNS,PS,QV2M,TS,CLRSKY_SFC_SW_DWN,ALLSKY_SFC_PAR_TOT,T2M_RANGE'
     if SUB == 'daily_grid' else 'T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,GWETROOT,EVPTRNS')
lats = [44.5 + 0.5*i for i in range(7)]
lons = [20.625 + 0.625*i for i in range(8)]
for la in lats:
    for lo in lons:
        f = f'{D}/power_daily_{la:.3f}_{lo:.3f}.csv'
        if os.path.exists(f) and os.path.getsize(f) > 1000: continue
        for attempt in range(4):
            r = requests.get('https://power.larc.nasa.gov/api/temporal/daily/point', params=dict(parameters=P, community='AG', latitude=la, longitude=lo, start=START, end=END, format='CSV'), timeout=300)
            if r.ok: open(f,'w').write(r.text); print('ok', f, len(r.text), flush=True); break
            print('retry', la, lo, r.status_code, r.text[:300], flush=True); time.sleep(10)
