"""INS TEMPO PPA102C: average farm-gate prices (lei/kg) of field crops, Romania + the
development regions of the study area, yearly 2015 onward. No account needed.

usage: prices.py <raw dir>   -> <raw>/crops/ins_tempo/PPA102C_prices.csv (+ metadata)
"""
import json
import os
import sys

import requests

B = 'http://statistici.insse.ro:8077/tempo-ins'
CODE = 'PPA102C'
PRODUCTS = {'Grau', 'Orz', 'Orzoaica', 'Orz - Orzoaica', 'Ovaz', 'Porumb boabe', 'Floarea soarelui', 'Soia', 'Rapita'}
REGIONS = {'TOTAL', 'Regiunea CENTRU', 'Regiunea NORD-VEST', 'Regiunea VEST', 'Regiunea SUD-VEST OLTENIA'}

D = os.path.expanduser(sys.argv[1]) + '/crops/ins_tempo'
os.makedirs(D, exist_ok=True)
m = requests.get(f'{B}/matrix/{CODE}', timeout=60).json()
json.dump(m, open(f'{D}/{CODE}_metadata.json', 'w'), ensure_ascii=False, indent=1)
parts = []
for dim in m['dimensionsMap']:
    lab = dim['label'].lower()
    opts = dim['options']
    if 'produse' in lab:
        opts = [o for o in opts if o['label'].strip() in PRODUCTS]
    elif 'regiuni' in lab:
        opts = [o for o in opts if o['label'].strip() in REGIONS]
    elif 'perioade' in lab:
        opts = [o for o in opts if o['label'].strip().startswith('Anul') and int(o['label'].split()[-1]) >= 2015]
    elif 'unitati' in lab:
        opts = [o for o in opts if o['label'].strip() == 'Lei / kg']
    parts.append(','.join(str(o['nomItemId']) for o in opts))
    print(' ', dim['label'], len(opts), flush=True)
body = dict(language='ro', encQuery=':'.join(parts), matCode=CODE, matMaxDim=m['details']['matMaxDim'],
            matUMSpec=m['details']['matUMSpec'], matRegJ=m['details'].get('matRegJ', 0))
r = requests.post(f'{B}/pivot', json=body, timeout=300)
print(' ', r.status_code, len(r.text), r.text[:300].replace('\n', ' | '), flush=True)
if r.ok:
    open(f'{D}/{CODE}_prices.csv', 'w').write(r.text)
