"""Load satellite vegetation for every saved field so the demo shows it instantly.

    cd backend && uv run python scripts/prewarm_fields.py

Runs the same imagery job the app runs (HLS + Sentinel-2, cached in .cache/fields/ for
12 h; past peak seasons are cached permanently). Needs internet and, for HLS, an
Earthdata login (~/.netrc or S2F_EARTHDATA_TOKEN).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.field import imagery  # noqa: E402
from app.field.geom import parse  # noqa: E402
from app.models import Field_  # noqa: E402


def main() -> None:
    init_db()
    with Session(engine) as s:
        fields = list(s.exec(select(Field_)))
    if not fields:
        print("No saved fields. Draw and save one in the app first.")
        return
    for f in fields:
        t = time.time()
        job = imagery.start(parse(json.loads(f.geometry_geojson)))
        while job.status in ("queued", "running"):
            time.sleep(3)
            print(f"\r  {f.name}: {job.stage} {job.done}/{job.total}   ", end="", flush=True)
        counts = {k: (v or {}).get("counts") for k, v in (job.result or {}).get("sources", {}).items()}
        print(f"\r  {f.name} ({f.area_ha} ha): {job.status} in {time.time() - t:.0f} s {counts}")


if __name__ == "__main__":
    main()
