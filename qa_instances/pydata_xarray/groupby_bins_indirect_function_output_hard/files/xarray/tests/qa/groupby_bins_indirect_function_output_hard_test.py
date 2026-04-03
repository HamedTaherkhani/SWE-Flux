from __future__ import annotations

import numpy as np
import xarray as xr


class TestGroupByBinsIndirectFunctionOutputHardQA:
    def test_groupby_bins_indirect_function_output_hard_case(self) -> None:
        signal = xr.DataArray(
            data=np.array([12, -5, 3, 7, 11, -2, 4], dtype=np.int64),
            dims=("obs",),
            coords={
                "score": ("obs", np.array([-4, -1, 0, 2, 6, 7, 11], dtype=np.int64)),
                "tag": ("obs", np.array(["u", "a", "b", "c", "d", "e", "v"])),
            },
            name="signal",
        )

        grouped = signal.groupby_bins(
            "score",
            bins=[-2, 0, 3, 5, 10],
            right=True,
            include_lowest=False,
        )
        reduced = grouped.sum()

        assert isinstance(reduced, xr.DataArray)
        assert "score_bins" in reduced.dims
        assert reduced.name == "signal"
