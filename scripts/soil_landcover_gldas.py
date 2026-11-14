import sys, pathlib, subprocess, urllib.parse, urllib.request
sys.path.insert(0, "scripts"); import edl

def soilgrids():
    props = ["clay","sand","silt","soc","phh2o","nitrogen","bdod","cec","cfvo","ocd"]
    depths = ["0-5cm","5-15cm","15-30cm","30-60cm"]
    for p in props:
        for d in depths:
            dest = pathlib.Path("data/soilgrids")/f"{p}_{d}_mean.tif"
            if dest.exists(): continue
            q = urllib.parse.urlencode([("map",f"/map/{p}.map"),("SERVICE","WCS"),("VERSION","2.0.1"),
                ("REQUEST","GetCoverage"),("COVERAGEID",f"{p}_{d}_mean"),("FORMAT","image/tiff"),
                ("SUBSETTINGCRS","http://www.opengis.net/def/crs/EPSG/0/4326"),
                ("OUTPUTCRS","http://www.opengis.net/def/crs/EPSG/0/4326"),
                ("SUBSET","Lat(45.6,46.5)"),("SUBSET","Long(23.0,24.2)")])
            try:
                b = urllib.request.urlopen("https://maps.isric.org/mapserv?"+q, timeout=300).read()
                dest.write_bytes(b); print(dest, len(b), flush=True)
            except Exception as e: print("ERR", dest, e, flush=True)

def worldcover():
    for t in ("N45E021", "N45E024"):
        u = f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
        dest = pathlib.Path("data/worldcover")/u.rsplit("/",1)[1]
        if not dest.exists():
            urllib.request.urlretrieve(u, dest)
        print(dest, dest.stat().st_size, flush=True)

def gldas():
    for e in edl.cmr("GLDAS_NOAH025_M", "2.1"):
        for u in edl.data_urls(e, suffixes=(".nc4",)):
            p = edl.download(u, pathlib.Path("data/gldas_monthly")/u.rsplit("/",1)[1]); print(p, p.stat().st_size, flush=True)

for f in (soilgrids, worldcover, gldas):
    try: f()
    except Exception as e: print("ERR", f.__name__, e, flush=True)
print("LCDONE", flush=True)
