import sys, os, json, requests
D = os.path.expanduser(sys.argv[1]) + '/crops/ins_tempo'; os.makedirs(D, exist_ok=True)
B = 'http://statistici.insse.ro:8077/tempo-ins'
COUNTIES = {'TOTAL','Alba','Arad','Bihor','Cluj','Hunedoara','Mures','Sibiu','Valcea'}
# usage: tempo.py <raw dir> CODE... ; env TEMPO_FROM=2000 fetches years from 2000 into <CODE>_AOI_<from>plus.csv
Y0 = int(os.environ.get('TEMPO_FROM', 2015))
for code in sys.argv[2:]:
    m = requests.get(f'{B}/matrix/{code}', timeout=60).json()
    print(code, m['matrixName'], flush=True)
    json.dump(m, open(f'{D}/{code}_metadata.json','w'), ensure_ascii=False, indent=1)
    parts = []
    for dim in m['dimensionsMap']:
        opts = dim['options']; lab = dim['label'].lower()
        if 'judet' in lab:
            opts = [o for o in opts if o['label'].strip() in COUNTIES]
        elif lab.startswith('ani') or 'perioade' in lab:
            opts = [o for o in opts if any(str(y) in o['label'] for y in range(Y0, 2027))]
        elif 'forme de proprietate' in lab:
            opts = opts[:1]
        parts.append(','.join(str(o['nomItemId']) for o in opts))
        print('  ', dim['label'], len(opts), flush=True)
    body = dict(language='ro', encQuery=':'.join(parts), matCode=code, matMaxDim=m['details']['matMaxDim'], matUMSpec=m['details']['matUMSpec'], matRegJ=m['details'].get('matRegJ', 0))
    r = requests.post(f'{B}/pivot', json=body, timeout=300)
    print('  ', r.status_code, len(r.text), r.text[:200].replace('\n',' | '), flush=True)
    if r.ok: open(f'{D}/{code}_AOI_{Y0}plus.csv','w').write(r.text)
