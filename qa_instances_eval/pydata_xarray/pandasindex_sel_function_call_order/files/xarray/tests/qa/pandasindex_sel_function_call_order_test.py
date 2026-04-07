from __future__ import annotations

import numpy as np
import pandas as pd

from xarray.core.indexes import PandasIndex


class TestPandasIndexSelFunctionCallOrderHardQA:
    def test_pandasindex_sel_function_call_order_case(self) -> None:
        pidx = PandasIndex(
            pd.Index([0, 2, 4, 8], name="x"),
            dim="x",
            coord_dtype=np.dtype("int64"),
        )

        first = pidx.sel({"x": 3}, method="nearest", tolerance=2)
        second = pidx.sel({"x": np.array([1, 7], dtype=np.int64)}, method="nearest", tolerance=2)

        assert "x" in first.dim_indexers
        assert "x" in second.dim_indexers
