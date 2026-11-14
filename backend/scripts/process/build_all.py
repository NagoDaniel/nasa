"""Run the whole processing pipeline: raw downloads -> compact JSON in backend/data/.

  uv run --group process python scripts/process/build_all.py            # all steps
  uv run --group process python scripts/process/build_all.py soil ins   # some steps
"""

from __future__ import annotations

import importlib
import sys
import time
import warnings

warnings.filterwarnings("ignore")

STEPS = ["units", "power", "imerg", "gldas", "firms", "agro_yearly", "soil", "ins", "cropmap", "ndvi"]


def main() -> None:
    wanted = sys.argv[1:] or STEPS
    for name in wanted:
        if name not in STEPS:
            raise SystemExit(f"unknown step '{name}', choose from {STEPS}")
        t = time.time()
        print(f"== {name}")
        importlib.import_module(name).main()
        print(f"   {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
