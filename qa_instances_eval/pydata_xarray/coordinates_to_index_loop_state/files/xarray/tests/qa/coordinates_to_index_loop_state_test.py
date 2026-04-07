from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr


class TestCoordinatesToIndexLoopStateHardQA:
    def test_coordinates_to_index_loop_state_case(self) -> None:
        midx = pd.MultiIndex.from_product(
            [["A", "B"], [1, 3]],
            names=["grp", "rank"],
        )
        mcoords = xr.Coordinates.from_pandas_multiindex(midx, "m")

        ds = xr.Dataset(
            data_vars={
                "v": (("m", "n"), np.arange(8, dtype=np.int64).reshape(4, 2)),
            },
            coords={"n": np.array([5, 9], dtype=np.int64)},
        ).assign_coords(mcoords)

        combined_index = ds.coords.to_index(ordered_dims=["n", "m"])

        assert isinstance(combined_index, pd.MultiIndex)
        assert combined_index.nlevels == 3
        assert len(combined_index) == 8
