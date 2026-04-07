from __future__ import annotations

import numpy as np
import xarray as xr


class TestApplyUfuncBroadcastInputShapeHardQA:
    def test_apply_ufunc_broadcast_input_shape_case(self) -> None:
        lhs = xr.DataArray(
            np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64),
            dims=("x", "y"),
            coords={"x": np.array([0, 1], dtype=np.int64), "y": np.array([10, 20, 30], dtype=np.int64)},
        )
        rhs = xr.DataArray(
            np.array(
                [
                    [0.5, 1.5, 2.5],
                    [3.5, 4.5, 5.5],
                    [6.5, 7.5, 8.5],
                    [9.5, 10.5, 11.5],
                ],
                dtype=np.float64,
            ),
            dims=("z", "y"),
            coords={"z": np.array([2, 4, 6, 8], dtype=np.int64), "y": np.array([10, 20, 30], dtype=np.int64)},
        )

        out = xr.apply_ufunc(
            lambda a, b: a + b,
            lhs,
            rhs,
            input_core_dims=[["y"], ["y"]],
            output_core_dims=[["y"]],
            vectorize=False,
        )
        observed_data_shape = list(out.data.shape)

        assert isinstance(out, xr.DataArray)
        assert set(out.dims) == {"x", "z", "y"}
        assert out.ndim == 3
        assert observed_data_shape == [2, 4, 3]
