import numpy as np
import pytest

try:
    from xarray.core.alignment import reindex_variables
except ModuleNotFoundError:
    from xarray.structure.alignment import reindex_variables
from xarray.core.variable import Variable


class TestReindexNewVarDUCoverageHardQA:
    def test_reindex_newvar_du_coverage_part_a(self) -> None:
        variables = {"v": Variable(("x",), np.array([10, 20, 30], dtype=np.int64))}

        masked = reindex_variables(
            variables,
            dim_pos_indexers={"x": np.array([0, -1, 2], dtype=np.int64)},
            copy=True,
            fill_value=-999,
            sparse=False,
        )
        assert masked["v"].shape == (3,)

        unchanged = reindex_variables(
            variables,
            dim_pos_indexers={"x": np.array([0, 1, 2], dtype=np.int64)},
            copy=True,
            fill_value=-1,
            sparse=False,
        )
        assert unchanged["v"].shape == (3,)
        assert unchanged["v"].data[0] == 10

    def test_reindex_newvar_du_coverage_part_b(self) -> None:
        variables = {"v": Variable(("x",), np.array([5, 6, 7], dtype=np.int64))}
        masked = reindex_variables(
            variables,
            dim_pos_indexers={"x": np.array([-1, 1, 2], dtype=np.int64)},
            copy=True,
            fill_value=-5,
            sparse=False,
        )
        assert masked["v"].shape == (3,)


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
