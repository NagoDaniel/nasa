import sys, os, time, requests
D = os.path.expanduser(sys.argv[1]) + '/nasa_power/daily_grid'; os.makedirs(D, exist_ok=True)
P = 'T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS2M,GWETTOP,GWETROOT,GWETPROF,EVPTRNS,PS,QV2M,TS,CLRSKY_SFC_SW_DWN,ALLSKY_SFC_PAR_TOT,T2M_RANGE'
lats = [44.5 + 0.5*i for i in range(7)]
lons = [20.625 + 0.625*i for i in range(8)]
for la in lats:
    for lo in lons:
        f = f'{D}/power_daily_{la:.3f}_{lo:.3f}.csv'
        if os.path.exists(f) and os.path.getsize(f) > 1000: continue
        for attempt in range(4):
            r = requests.get('https://power.larc.nasa.gov/api/temporal/daily/point', params=dict(parameters=P, community='AG', latitude=la, longitude=lo, start='20150101', end='20251231', format='CSV'), timeout=300)
            if r.ok: open(f,'w').write(r.text); print('ok', f, len(r.text), flush=True); break
            print('retry', la, lo, r.status_code, r.text[:300], flush=True); time.sleep(10)
