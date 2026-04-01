from __future__ import annotations

import numpy as np

from xarray.core.variable import Variable, calculate_dimensions


class TestCalculateDimensionsLoopIterationsHardQA:
    def test_calculate_dimensions_loop_iterations_hard_case(self) -> None:
        variables = {
            "temp": Variable(("time", "lat", "lon"), np.zeros((3, 2, 4), dtype=np.float64)),
            "precip": Variable(("time", "lat", "lon"), np.ones((3, 2, 4), dtype=np.float64)),
            "bias": Variable(("lat", "lon"), np.full((2, 4), 7, dtype=np.int64)),
            "station": Variable(("station",), np.array([101, 102, 103, 104, 105], dtype=np.int64)),
            "flag": Variable((), np.array(1, dtype=np.int64)),
            "mix": Variable(("time", "station"), np.arange(15, dtype=np.int64).reshape(3, 5)),
        }

        dims = calculate_dimensions(variables)

        assert isinstance(dims, dict)
        assert dims["time"] == 3
        assert dims["lat"] == 2
        assert dims["lon"] == 4
        assert dims["station"] == 5
