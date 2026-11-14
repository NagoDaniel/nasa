#!/bin/bash
D=$1/soil/soilgrids; mkdir -p $D; cd $D
for v in soc phh2o clay sand silt nitrogen bdod cec ocd cfvo; do for d in 0-5cm 5-15cm 15-30cm 30-60cm; do
 f=${v}_${d}_mean.tif; [ -s $f ] && continue
 curl -sf --retry 3 -o $f "https://maps.isric.org/mapserv?map=/map/${v}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=${v}_${d}_mean&FORMAT=GEOTIFF_INT16&SUBSET=long(20.6,25.4)&SUBSET=lat(44.4,47.7)&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326" && echo "ok $f $(stat -f%z $f)" || echo "FAIL $f"
done; done
