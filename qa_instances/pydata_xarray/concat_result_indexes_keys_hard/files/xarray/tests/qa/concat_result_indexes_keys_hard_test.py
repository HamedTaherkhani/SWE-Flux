from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr


class TestConcatResultIndexesKeysHardQA:
    def test_concat_result_indexes_keys_hard_case(self) -> None:
        midx = pd.MultiIndex.from_product(
            [["A", "B"], [1, 3]],
            names=["grp", "rank"],
        )
        mcoords = xr.Coordinates.from_pandas_multiindex(midx, "m")

        ds1 = xr.Dataset(
            data_vars={
                "signal": (("m", "x"), np.array([[1, 2], [3, 4], [5, 6], [7, 8]], dtype=np.int64)),
                "noise": ("x", np.array([10, 20], dtype=np.int64)),
            },
            coords={"x": np.array([0, 2], dtype=np.int64)},
        ).assign_coords(mcoords)

        ds2 = xr.Dataset(
            data_vars={
                "signal": (("m", "x"), np.array([[9, 10], [11, 12], [13, 14], [15, 16]], dtype=np.int64)),
                "noise": ("x", np.array([30, 40], dtype=np.int64)),
            },
            coords={"x": np.array([2, 4], dtype=np.int64)},
        ).assign_coords(mcoords)

        ds3 = xr.Dataset(
            data_vars={
                "signal": (("m", "x"), np.array([[17, 18], [19, 20], [21, 22], [23, 24]], dtype=np.int64)),
                "noise": ("x", np.array([50, 60], dtype=np.int64)),
            },
            coords={"x": np.array([4, 6], dtype=np.int64)},
        ).assign_coords(mcoords)

        merged = xr.concat(
            [ds1, ds2, ds3],
            dim=pd.Index(["b0", "b1", "b2"], name="batch"),
            data_vars="all",
            coords="different",
            join="outer",
            fill_value=-99,
        )

        assert isinstance(merged, xr.Dataset)
        assert merged.sizes["batch"] == 3
        assert "signal" in merged.data_vars
        assert "noise" in merged.data_vars
