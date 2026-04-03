from __future__ import annotations

import numpy as np
import xarray as xr


class TestDatasetRollingConstructExecutionPathHardQA:
    def test_dataset_rolling_construct_execution_path_hard_case(self) -> None:
        ds = xr.Dataset(
            data_vars={
                "signal": (
                    ("x", "y"),
                    np.array(
                        [
                            [1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9],
                            [10, 11, 12],
                        ],
                        dtype=np.int64,
                    ),
                ),
                "meta": ("z", np.array([100, 200], dtype=np.int64)),
            },
            coords={
                "x": np.array([0, 1, 2, 3], dtype=np.int64),
                "y": np.array([10, 20, 30], dtype=np.int64),
                "z": np.array([9, 8], dtype=np.int64),
            },
        )

        out = ds.rolling(x=3, center=True).construct(
            window_dim="win",
            stride=2,
            fill_value=-1,
            keep_attrs=False,
        )

        assert isinstance(out, xr.Dataset)
        assert "signal" in out.data_vars
        assert "meta" in out.data_vars
        assert "win" in out["signal"].dims
