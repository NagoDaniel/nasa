"""Small AppEEARS sample requests (Alba county) so development can start before the full requests finish.
Usage: python samples.py <data_dir> <state_json> [submit|wait]"""
import json, netrc, os, sys, time
import requests
from shapely.geometry import shape, mapping
API = 'https://appeears.earthdatacloud.nasa.gov/api'
D = os.path.expanduser(sys.argv[1]); STATE = sys.argv[2]; MODE = sys.argv[3]
l, _, p = netrc.netrc().authenticators('urs.earthdata.nasa.gov')
H = {'Authorization': 'Bearer ' + requests.post(f'{API}/login', auth=(l, p), timeout=60).json()['token']}
f = [x for x in json.load(open(f'{D}/boundaries/aoi_counties.geojson'))['features'] if x['properties']['shapeName'] == 'ALBA'][0]
f['geometry'] = mapping(shape(f['geometry']).simplify(0.005))
ALBA = {'type': 'FeatureCollection', 'features': [f]}
def L(prod, *ls): return [{'product': prod, 'layer': x} for x in ls]
Y24 = [{'startDate': '01-01-2024', 'endDate': '12-31-2024'}]
JUL = [{'startDate': '07-01-2024', 'endDate': '07-31-2024'}]
TASKS = {
    'vegetation/modis_mod13q1_ndvi_evi': (Y24, L('MOD13Q1.061', '_250m_16_days_NDVI', '_250m_16_days_EVI', '_250m_16_days_pixel_reliability'), 'geotiff'),
    'evapotranspiration/modis_mod16a2gf_et_500m': (Y24, L('MOD16A2GF.061', 'ET_500m', 'PET_500m', 'ET_QC_500m'), 'geotiff'),
    'temperature/modis_mod11a2_lst_1km': (Y24, L('MOD11A2.061', 'LST_Day_1km', 'LST_Night_1km', 'QC_Day'), 'geotiff'),
    'terrain/srtm_gl1_30m': ([{'startDate': '02-11-2000', 'endDate': '02-21-2000'}], L('SRTMGL1_NC.003', 'SRTMGL1_DEM'), 'geotiff'),
    'soil_moisture/smap_l3_enhanced_9km_daily': (Y24, L('SPL3SMP_E.006', 'Soil_Moisture_Retrieval_Data_AM_soil_moisture', 'Soil_Moisture_Retrieval_Data_PM_soil_moisture_pm', 'Soil_Moisture_Retrieval_Data_AM_retrieval_qual_flag'), 'netcdf4'),
    'soil_moisture/smap_l4_9km_3hourly_rootzone': (JUL, L('SPL4SMGP.008', 'Geophysical_Data_sm_surface', 'Geophysical_Data_sm_rootzone', 'Geophysical_Data_sm_rootzone_pctl'), 'netcdf4'),
    'evapotranspiration/ecostress_et_esi_70m_alba': (JUL, L('ECO_L3T_JET.002', 'ETdaily') + L('ECO_L4T_ESI.002', 'ESI', 'cloud'), 'geotiff'),
    'vegetation/hls_30m_ndvi_alba': (JUL, L('HLSL30_VI.020', 'NDVI') + L('HLSS30_VI.020', 'NDVI') + L('HLSL30.020', 'Fmask') + L('HLSS30.020', 'Fmask'), 'geotiff'),
}
state = json.load(open(STATE)) if os.path.exists(STATE) else {}
if MODE == 'submit':
    for name, (dates, layers, fmt) in TASKS.items():
        if name in state: continue
        body = {'task_type': 'area', 'task_name': 'fieldshift_SAMPLE_' + name.replace('/', '_'),
                'params': {'dates': dates, 'layers': layers, 'geo': ALBA, 'output': {'format': {'type': fmt}, 'projection': 'geographic'}}}
        r = requests.post(f'{API}/task', json=body, headers=H, timeout=120)
        print('submit', name, r.status_code, r.text[:200], flush=True)
        if r.ok: state[name] = {'task_id': r.json()['task_id'], 'done': False}
        json.dump(state, open(STATE, 'w'), indent=1); time.sleep(2)
    sys.exit()
while not all(v['done'] for v in state.values()):
    for name, v in state.items():
        if v['done']: continue
        st = requests.get(f"{API}/task/{v['task_id']}", headers=H, timeout=60).json().get('status')
        if st in ('error', 'expired'): print('FAILED', name, flush=True); v['done'] = True; continue
        if st != 'done': continue
        od = f'{D}/_samples/{name}'; os.makedirs(od, exist_ok=True)
        for fl in requests.get(f"{API}/bundle/{v['task_id']}", headers=H, timeout=60).json()['files']:
            out = os.path.join(od, fl['file_name']); os.makedirs(os.path.dirname(out), exist_ok=True)
            with requests.get(f"{API}/bundle/{v['task_id']}/{fl['file_id']}", headers=H, stream=True, timeout=600) as rr:
                rr.raise_for_status()
                with open(out, 'wb') as o:
                    for c in rr.iter_content(1 << 20): o.write(c)
        v['done'] = True; json.dump(state, open(STATE, 'w'), indent=1); print('DONE', name, flush=True)
    time.sleep(60)
print('ALL DONE', flush=True)
