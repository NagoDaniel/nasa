import sys, os, rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
D = os.path.expanduser(sys.argv[1]) + '/crops/eucropmap'; os.makedirs(D, exist_ok=True)
B = '/vsicurl/https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EUCROPMAP'
for name, src in [('EUCROPMAP_2022_AOI.tif', f'{B}/2022/EU_CropMap_22_v1_stratum_EU27-HR.tif'), ('EUCROPMAP_2018_AOI.tif', f'{B}/2018/EUCROPMAP_2018.tif')]:
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_MULTIRANGE='YES', CPL_VSIL_CURL_CHUNK_SIZE=1048576):
        with rasterio.open(src) as r:
            print(name, r.crs, r.res, r.shape, r.profile.get('tiled'), r.profile.get('blockxsize'), flush=True)
            b = transform_bounds('EPSG:4326', r.crs, 20.6, 44.4, 25.4, 47.7)
            w = from_bounds(*b, r.transform).round_offsets().round_lengths()
            a = r.read(1, window=w)
            p = r.profile.copy(); p.update(height=a.shape[0], width=a.shape[1], transform=r.window_transform(w), compress='deflate', tiled=True, blockxsize=512, blockysize=512, driver='GTiff')
            with rasterio.open(f'{D}/{name}', 'w', **p) as o: o.write(a, 1)
            print('ok', name, a.shape, flush=True)
