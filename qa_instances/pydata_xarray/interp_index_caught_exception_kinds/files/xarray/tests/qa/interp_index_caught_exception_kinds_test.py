from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from xarray.core.missing import get_clean_interp_index


class TestInterpIndexCaughtExceptionKindsHardQA:
    def test_interp_index_caught_exception_kinds_case(self) -> None:
        arr_multi = xr.DataArray(
            np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64),
            dims=("m",),
            coords={
                "m": pd.MultiIndex.from_product(
                    [["g1", "g2"], [0, 1]],
                    names=["grp", "pos"],
                )
            },
        )

        arr_str = xr.DataArray(
            np.array([10.0, 20.0, 30.0], dtype=np.float64),
            dims=("x",),
            coords={"x": np.array(["s0", "s1", "s2"], dtype=object)},
        )

        with pytest.raises(TypeError):
            get_clean_interp_index(arr_multi, "m", use_coordinate=True, strict=False)
        with pytest.raises(TypeError):
            get_clean_interp_index(arr_str, "x", use_coordinate=True, strict=False)
