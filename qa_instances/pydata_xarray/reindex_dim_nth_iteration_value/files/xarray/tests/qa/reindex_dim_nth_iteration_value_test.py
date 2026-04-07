import numpy as np

try:
    from xarray.core.alignment import reindex_variables
except ModuleNotFoundError:
    from xarray.structure.alignment import reindex_variables
from xarray.core.variable import Variable


class TestReindexDimNthIterationValueHardQA:
    def test_reindex_dim_nth_iteration_value_case(self) -> None:
        variables = {
            "v": Variable(
                ("x", "y"),
                np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int64),
            )
        }

        out = reindex_variables(
            variables=variables,
            dim_pos_indexers={
                "x": np.array([0, -1], dtype=np.int64),
                "y": np.array([2, 1, 0], dtype=np.int64),
            },
            copy=True,
            fill_value=-999,
            sparse=False,
        )
        assert out["v"].shape == (2, 3)
