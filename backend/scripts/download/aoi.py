import json, sys
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
D = sys.argv[1]
a1 = json.load(open(f'{D}/boundaries/ROU_ADM1.geojson'))
print(sorted(f['properties']['shapeName'] for f in a1['features']))
want = ['ALBA','CLUJ','MURES','SIBIU','HUNEDOARA','ARAD','BIHOR','VALCEA']
norm = lambda s: s.replace('ş','ș').replace('ţ','ț').replace(' County','').replace('Judetul ','').strip()
sel = [f for f in a1['features'] if norm(f['properties']['shapeName']) in want]
print('selected', [f['properties']['shapeName'] for f in sel])
for f in sel: f['geometry'] = mapping(shape(f['geometry']).simplify(0.001))
json.dump({'type':'FeatureCollection','features':sel}, open(f'{D}/boundaries/aoi_counties.geojson','w'))
u = unary_union([shape(f['geometry']) for f in sel])
print('bbox', u.bounds)
json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'name':'Alba+neighbours'},'geometry':mapping(u)}]}, open(f'{D}/boundaries/aoi_union.geojson','w'))
a2 = json.load(open(f'{D}/boundaries/ROU_ADM2.geojson'))
out=[]
for f in a2['features']:
    g = shape(f['geometry'])
    p = g.representative_point()
    for c in sel:
        if shape(c['geometry']).contains(p):
            f['properties']['county'] = norm(c['properties']['shapeName'])
            f['geometry'] = mapping(g.simplify(0.0005)); out.append(f); break
print('communes', len(out))
json.dump({'type':'FeatureCollection','features':out}, open(f'{D}/boundaries/aoi_communes.geojson','w'))
