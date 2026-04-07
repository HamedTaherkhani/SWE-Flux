from __future__ import annotations

import numpy as np
import xarray as xr


class TestMapIndexQueriesConcreteSelDispatchHardQA:
    def test_map_index_queries_concrete_sel_dispatch_case(self) -> None:
        ds = xr.Dataset(
            {
                "v": (
                    ("lat", "lon", "time"),
                    np.arange(24, dtype=np.int64).reshape(2, 3, 4),
                )
            },
            coords={
                "lat": np.array(["A", "B"], dtype=object),
                "lon": np.array([10, 20, 30], dtype=np.int64),
                "time": np.array([0, 1, 2, 3], dtype=np.int64),
            },
        )

        stacked = ds.stack(cell=("lat", "lon"))
        selected = stacked.sel(
            time=slice(1, 3),
            cell={"lat": "B"},
        )

        assert isinstance(selected, xr.Dataset)
        assert selected.sizes["time"] == 3
        assert "lon" in selected.dims
        assert selected.sizes["lon"] == 3
