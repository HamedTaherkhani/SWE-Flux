from __future__ import annotations

import numpy as np
import xarray as xr


class TestAlignExactReindexAllReachabilityHardQA:
    def test_align_exact_reindexall_reachability_case(self) -> None:
        left = xr.DataArray(
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64),
            dims=("x", "y"),
            coords={"x": np.array([0, 1], dtype=np.int64), "y": np.array([10, 20], dtype=np.int64)},
        )
        right = xr.DataArray(
            np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float64),
            dims=("x", "y"),
            coords={"x": np.array([0, 1], dtype=np.int64), "y": np.array([10, 20], dtype=np.int64)},
        )

        out_left, out_right = xr.align(left, right, join="exact", copy=False)

        assert out_left is left
        assert out_right is right
