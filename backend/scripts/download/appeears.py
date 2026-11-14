"""Submit AppEEARS area requests for the AOI, wait for them, download the bundles.
Usage: python appeears.py <data_dir> <state_json>
Credentials come from ~/.netrc (machine urs.earthdata.nasa.gov)."""
import json, netrc, os, sys, time
import requests
from shapely.geometry import shape, mapping

API = 'https://appeears.earthdatacloud.nasa.gov/api'
D = os.path.expanduser(sys.argv[1])
STATE = sys.argv[2]

login, _, pw = netrc.netrc().authenticators('urs.earthdata.nasa.gov')
tok = requests.post(f'{API}/login', auth=(login, pw), timeout=60)
tok.raise_for_status()
H = {'Authorization': f"Bearer {tok.json()['token']}"}


def fc(path, county=None, tol=0.01):
    feats = json.load(open(path))['features']
    if county:
        feats = [f for f in feats if f['properties']['shapeName'] == county]
    out = []
    for f in feats:
        f = dict(f)
        f['geometry'] = mapping(shape(f['geometry']).simplify(tol))
        out.append(f)
    return {'type': 'FeatureCollection', 'features': out}


AOI = fc(f'{D}/boundaries/aoi_union.geojson')
ALBA = fc(f'{D}/boundaries/aoi_counties.geojson', county='ALBA', tol=0.005)
FULL = [{'startDate': '01-01-2015', 'endDate': '12-31-2025'}]
SEASON_ECO = [{'startDate': '04-01', 'endDate': '09-30', 'recurring': True, 'yearRange': [2018, 2025]}]
SEASON_HLS = [{'startDate': '04-01', 'endDate': '09-30', 'recurring': True, 'yearRange': [2023, 2025]}]


def L(product, *layers):
    return [{'product': product, 'layer': l} for l in layers]


TASKS = {
    'vegetation/modis_mod13q1_ndvi_evi': (AOI, FULL, L('MOD13Q1.061', '_250m_16_days_NDVI', '_250m_16_days_EVI', '_250m_16_days_pixel_reliability'), 'geotiff'),
    'evapotranspiration/modis_mod16a2gf_et_500m': (AOI, FULL, L('MOD16A2GF.061', 'ET_500m', 'PET_500m', 'ET_QC_500m'), 'geotiff'),
    'temperature/modis_mod11a2_lst_1km': (AOI, FULL, L('MOD11A2.061', 'LST_Day_1km', 'LST_Night_1km', 'QC_Day'), 'geotiff'),
    'terrain/srtm_gl1_30m': (AOI, [{'startDate': '02-11-2000', 'endDate': '02-21-2000'}], L('SRTMGL1_NC.003', 'SRTMGL1_DEM'), 'geotiff'),
    'vegetation/hls_30m_ndvi_alba': (ALBA, SEASON_HLS, L('HLSL30_VI.020', 'NDVI') + L('HLSS30_VI.020', 'NDVI') + L('HLSL30.020', 'Fmask') + L('HLSS30.020', 'Fmask'), 'geotiff'),
}

for y in range(2015, 2026):
    yr = [{'startDate': f'01-01-{y}', 'endDate': f'12-31-{y}'}]
    TASKS[f'soil_moisture/smap_l3_enhanced_9km_daily/{y}'] = (AOI, yr, L('SPL3SMP_E.006', 'Soil_Moisture_Retrieval_Data_AM_soil_moisture', 'Soil_Moisture_Retrieval_Data_PM_soil_moisture_pm', 'Soil_Moisture_Retrieval_Data_AM_retrieval_qual_flag'), 'netcdf4')
    TASKS[f'soil_moisture/smap_l4_9km_3hourly_rootzone/{y}'] = (AOI, yr, L('SPL4SMGP.008', 'Geophysical_Data_sm_surface', 'Geophysical_Data_sm_rootzone', 'Geophysical_Data_sm_rootzone_pctl'), 'netcdf4')
for y in range(2018, 2026):
    for half, (a, b) in enumerate([('04-01', '06-30'), ('07-01', '09-30')]):
        TASKS[f'evapotranspiration/ecostress_et_esi_70m_alba/{y}_{half + 1}'] = (ALBA, [{'startDate': f'{a}-{y}', 'endDate': f'{b}-{y}'}], L('ECO_L3T_JET.002', 'ETdaily') + L('ECO_L4T_ESI.002', 'ESI', 'cloud'), 'geotiff')
state = json.load(open(STATE)) if os.path.exists(STATE) else {}
for name, (geo, dates, layers, fmt) in TASKS.items():
    if name in state:
        continue
    body = {'task_type': 'area', 'task_name': 'fieldshift_' + name.replace('/', '_'),
            'params': {'dates': dates, 'layers': layers, 'geo': geo, 'output': {'format': {'type': fmt}, 'projection': 'geographic'}}}
    r = requests.post(f'{API}/task', json=body, headers=H, timeout=120)
    print('submit', name, r.status_code, r.text[:300], flush=True)
    time.sleep(2)
    if r.ok:
        state[name] = {'task_id': r.json()['task_id'], 'done': False}
        json.dump(state, open(STATE, 'w'), indent=1)

while not all(v['done'] for v in state.values()):
    for name, v in state.items():
        if v['done']:
            continue
        st = requests.get(f"{API}/task/{v['task_id']}", headers=H, timeout=60).json()
        status = st.get('status')
        if status in ('error', 'expired'):
            print('FAILED', name, json.dumps(st)[:500], flush=True)
            v['done'] = True
            continue
        if status != 'done':
            continue
        od = f'{D}/{name}'
        os.makedirs(od, exist_ok=True)
        files = requests.get(f"{API}/bundle/{v['task_id']}", headers=H, timeout=60).json()['files']
        print('downloading', name, len(files), 'files', flush=True)
        for f in files:
            out = os.path.join(od, f['file_name'])
            if os.path.exists(out) and os.path.getsize(out) == f.get('file_size', -1):
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            for attempt in range(4):
                try:
                    with requests.get(f"{API}/bundle/{v['task_id']}/{f['file_id']}", headers=H, stream=True, timeout=600) as rr:
                        rr.raise_for_status()
                        with open(out, 'wb') as o:
                            for chunk in rr.iter_content(1 << 20):
                                o.write(chunk)
                    break
                except Exception as e:
                    print('retry', out, e, flush=True)
                    time.sleep(10)
        v['done'] = True
        json.dump(state, open(STATE, 'w'), indent=1)
        print('DONE', name, flush=True)
    print(time.strftime('%H:%M'), {k: v['done'] for k, v in state.items()}, flush=True)
    time.sleep(120)
print('ALL DONE', flush=True)
