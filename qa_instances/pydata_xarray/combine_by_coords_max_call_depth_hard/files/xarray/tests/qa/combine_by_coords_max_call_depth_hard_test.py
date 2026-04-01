from __future__ import annotations

import numpy as np
import xarray as xr


class TestCombineByCoordsMaxCallDepthHardQA:
    def test_combine_by_coords_max_call_depth_hard_case(self) -> None:
        time_a = np.array([0, 1], dtype=np.int64)
        time_b = np.array([2, 3], dtype=np.int64)
        x_a = np.array([10, 20], dtype=np.int64)
        x_b = np.array([30, 40], dtype=np.int64)

        ds_00 = xr.Dataset(
            {"temp": (("time", "x"), np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64))},
            coords={"time": time_a, "x": x_a},
        )
        ds_01 = xr.Dataset(
            {"temp": (("time", "x"), np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float64))},
            coords={"time": time_a, "x": x_b},
        )
        ds_10 = xr.Dataset(
            {"temp": (("time", "x"), np.array([[9.0, 10.0], [11.0, 12.0]], dtype=np.float64))},
            coords={"time": time_b, "x": x_a},
        )
        ds_11 = xr.Dataset(
            {"temp": (("time", "x"), np.array([[13.0, 14.0], [15.0, 16.0]], dtype=np.float64))},
            coords={"time": time_b, "x": x_b},
        )

        combined = xr.combine_by_coords(
            [ds_10, ds_01, ds_11, ds_00],
            fill_value=-999.0,
            combine_attrs="no_conflicts",
        )

        assert isinstance(combined, xr.Dataset)
        assert combined.sizes["time"] == 4
        assert combined.sizes["x"] == 4
        assert "temp" in combined.data_vars
