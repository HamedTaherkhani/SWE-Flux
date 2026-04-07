from __future__ import annotations

import numpy as np
import xarray as xr


class TestRollingTempDimValueSequenceHardQA:
    def test_rolling_temp_dim_value_sequence_case(self) -> None:
        base = xr.DataArray(
            np.arange(60, dtype=np.float64).reshape(5, 4, 3),
            dims=("x", "_rolling_dim_x", "__rolling_dim_x"),
            coords={
                "x": np.arange(5, dtype=np.int64),
                "_rolling_dim_x": np.arange(4, dtype=np.int64),
                "__rolling_dim_x": np.arange(3, dtype=np.int64),
            },
        )

        with_more_collisions = base.expand_dims(
            {"___rolling_dim_x": np.array([0, 1], dtype=np.int64)}
        )

        reduced = with_more_collisions.rolling(x=3, center=True, min_periods=1).reduce(np.sum)

        assert isinstance(reduced, xr.DataArray)
        assert "x" in reduced.dims
        assert reduced.sizes["x"] == 5
