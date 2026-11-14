import sys
from pathlib import Path

import numpy as np
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "process"))
import common  # noqa: E402


def test_weights_follow_overlap(monkeypatch):
    units = (
        common.Unit("A", "county", "A", "A", box(0, 0, 1, 1)),        # exactly one cell
        common.Unit("B", "county", "B", "B", box(0.5, 0, 1.5, 1)),    # half of two cells
    )
    monkeypatch.setattr(common, "load_units", lambda: units)
    gw = common.grid_weights([0.5], [0.5, 1.5], 1.0, 1.0)
    cells, w = gw.units["A"]
    assert list(cells) == [0] and np.allclose(w, [1.0])
    cells, w = gw.units["B"]
    assert sorted(cells) == [0, 1] and np.allclose(sorted(w), [0.5, 0.5])
    vals = np.array([[[10.0, 20.0]]])  # (time, lat, lon)
    agg = common.aggregate(vals, gw)
    assert np.allclose(agg["A"], [10.0]) and np.allclose(agg["B"], [15.0])


def test_aggregate_ignores_nan(monkeypatch):
    units = (common.Unit("B", "county", "B", "B", box(0.5, 0, 1.5, 1)),)
    monkeypatch.setattr(common, "load_units", lambda: units)
    gw = common.grid_weights([0.5], [0.5, 1.5], 1.0, 1.0)
    agg = common.aggregate(np.array([[[np.nan, 20.0]]]), gw)
    assert np.allclose(agg["B"], [20.0])
