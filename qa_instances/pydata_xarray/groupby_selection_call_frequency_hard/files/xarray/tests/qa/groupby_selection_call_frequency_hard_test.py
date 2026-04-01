from __future__ import annotations

import numpy as np
import xarray as xr


class TestGroupBySelectionCallFrequencyHardQA:
    def test_groupby_selection_call_frequency_hard_case(self) -> None:
        arr = xr.DataArray(
            np.array([2, 4, 6, 8, 10], dtype=np.int64),
            dims=("obs",),
            coords={
                "grp": ("obs", np.array(["a", "c", "a", "b", "c"], dtype=object)),
            },
        )

        weights = xr.DataArray(
            np.array([1.0, 2.0, 3.0], dtype=np.float64),
            dims=("grp",),
            coords={"grp": np.array(["a", "b", "z"], dtype=object)},
        )

        result = xr.apply_ufunc(
            lambda x, w: x * w,
            arr.groupby("grp"),
            weights,
            vectorize=True,
            output_dtypes=[np.float64],
        )

        assert isinstance(result, xr.DataArray)
        assert "obs" in result.dims
        assert "grp" in result.coords
