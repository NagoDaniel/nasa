"""AOI subsets of GPM IMERG (daily + monthly) and GLDAS Noah monthly via GES DISC OPeNDAP.
Usage: python gesdisc.py <data_dir> [probe]"""
import calendar, os, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

D = os.path.expanduser(sys.argv[1])
PROBE = len(sys.argv) > 2
s = requests.Session()  # ~/.netrc is used for the URS redirect

# IMERG 0.1 deg grid, dims [time][lon][lat]; AOI 20.55-25.45E, 44.35-47.75N
ILON, ILAT = '2005:1:2054', '1343:1:1377'
# GLDAS 0.25 deg grid, dims [time][lat][lon]; lon from -179.875, lat from -59.875
GLON, GLAT = '802:1:821', '417:1:430'
GVARS = ['SoilMoi0_10cm_inst', 'SoilMoi10_40cm_inst', 'SoilMoi40_100cm_inst', 'RootMoist_inst', 'Evap_tavg', 'PotEvap_tavg',
         'Rainf_f_tavg', 'Tair_f_inst', 'Qair_f_inst', 'ESoil_tavg', 'Tveg_tavg', 'ECanop_tavg', 'SWdown_f_tavg']


def ce_imerg(var_list):
    parts = [f'/{v}[0:1:0][{ILON}][{ILAT}]' for v in var_list] + [f'/lon[{ILON}]', f'/lat[{ILAT}]', '/time']
    return ';'.join(parts)


def ce_gldas():
    return ';'.join([f'/{v}[0:1:0][{GLAT}][{GLON}]' for v in GVARS] + [f'/lon[{GLON}]', f'/lat[{GLAT}]', '/time'])


jobs = []
for y in range(2015, 2026):
    for m in range(1, 13):
        jobs.append((f'https://opendap.earthdata.nasa.gov/collections/C2723754851-GES_DISC/granules/GPM_3IMERGM.07%3A3B-MO.MS.MRG.3IMERG.{y}{m:02d}01-S000000-E235959.{m:02d}.V07B.HDF5.dap.nc4',
                     f'/Grid/precipitation[0:1:0][{ILON}][{ILAT}];/Grid/lon[{ILON}];/Grid/lat[{ILAT}];/Grid/time',
                     f'{D}/precipitation/gpm_imerg_monthly/IMERG_monthly_{y}{m:02d}_AOI.nc4'))
        jobs.append((f'https://opendap.earthdata.nasa.gov/collections/C1342986036-GES_DISC/granules/GLDAS_NOAH025_M.2.1%3AGLDAS_NOAH025_M.A{y}{m:02d}.021.nc4.dap.nc4',
                     ce_gldas(), f'{D}/land_model/gldas_noah025_monthly/GLDAS_NOAH025_M_{y}{m:02d}_AOI.nc4'))
        for d in range(1, calendar.monthrange(y, m)[1] + 1):
            jobs.append((f'https://opendap.earthdata.nasa.gov/collections/C2723754864-GES_DISC/granules/GPM_3IMERGDF.07%3A3B-DAY.MS.MRG.3IMERG.{y}{m:02d}{d:02d}-S000000-E235959.V07B.nc4.dap.nc4',
                         ce_imerg(['precipitation', 'randomError']), f'{D}/precipitation/gpm_imerg_daily/{y}/IMERG_daily_{y}{m:02d}{d:02d}_AOI.nc4'))


def fetch(job):
    url, ce, out = job
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for attempt in range(4):
        try:
            r = s.get(url + '?dap4.ce=' + requests.utils.quote(ce, safe=''), timeout=300)
            if r.ok and r.content[:4] == b'\x89HDF':
                open(out, 'wb').write(r.content)
                print('ok', out, len(r.content), flush=True)
                return
            print('err', r.status_code, url, r.text[:200].replace('\n', ' '), flush=True)
            if r.status_code in (400, 404):
                return
        except Exception as e:
            print('exc', url, e, flush=True)
        time.sleep(5 * (attempt + 1))


if PROBE:
    picks = [j for j in jobs if '201507' in j[2] or '20150715' in j[2]][:3]
    for j in picks:
        fetch(j)
else:
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(fetch, jobs))
    print('ALL DONE', flush=True)
