from __future__ import annotations

import numpy as np
import xarray as xr


class TestAlignOuterMaxCallDepthHardQA:
    def test_align_outer_max_call_depth_hard_case(self) -> None:
        a = xr.DataArray(
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64),
            dims=("time", "x"),
            coords={"time": [0, 1], "x": [10, 20]},
            name="a",
        )
        b = xr.DataArray(
            np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float64),
            dims=("time", "x"),
            coords={"time": [1, 2], "x": [20, 30]},
            name="b",
        )
        c = xr.DataArray(
            np.array([[9.0, 10.0], [11.0, 12.0]], dtype=np.float64),
            dims=("time", "x"),
            coords={"time": [2, 3], "x": [30, 40]},
            name="c",
        )

        a2, b2, c2 = xr.align(a, b, c, join="outer", copy=False, fill_value=-999.0)

        assert a2.sizes["time"] == 4 and a2.sizes["x"] == 4
        assert b2.sizes["time"] == 4 and b2.sizes["x"] == 4
        assert c2.sizes["time"] == 4 and c2.sizes["x"] == 4
