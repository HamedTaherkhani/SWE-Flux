from __future__ import annotations

import numpy as np
import xarray as xr


class TestReindexVariablesInputStateIndirectHardQA:
    def test_reindex_variables_input_state_indirect_case(self) -> None:
        ds = xr.Dataset(
            data_vars={
                "temp": (
                    ("x", "y"),
                    np.array(
                        [
                            [1.0, 2.0, 3.0],
                            [4.0, 5.0, 6.0],
                            [7.0, 8.0, 9.0],
                            [10.0, 11.0, 12.0],
                        ],
                        dtype=np.float64,
                    ),
                ),
                "quality": ("x", np.array([0, 1, 1, 0], dtype=np.int64)),
            },
            coords={
                "x": np.array([0, 1, 2, 3], dtype=np.int64),
                "y": np.array([10, 20, 30], dtype=np.int64),
            },
        )

        out = ds.reindex(
            x=np.array([2, 5, 0, 3], dtype=np.int64),
            y=np.array([20, 99, 10], dtype=np.int64),
            fill_value={"temp": -9.5, "quality": -7},
        )

        assert isinstance(out, xr.Dataset)
        assert out.sizes["x"] == 4
        assert out.sizes["y"] == 3
        assert "temp" in out.data_vars
        assert "quality" in out.data_vars
