import pytest
import numpy as np

from xarray.core.formatting import first_n_items
from xarray.core.variable import Variable


class TestRollingExpBranchProfileHardQA:
    def test_rolling_exp_branch_profile_hard_case(self) -> None:
        out_head = first_n_items(np.arange(6), 3)
        out_full = first_n_items(np.arange(2), 5)
        out_empty = first_n_items(np.array([]), 1)
        out_var = first_n_items(Variable(("x",), np.array([4, 5, 6])), 2)

        assert out_head.tolist() == [0, 1, 2]
        assert out_full.tolist() == [0, 1]
        assert out_empty == []
        assert out_var.tolist() == [4, 5]

        with pytest.raises(ValueError):
            first_n_items(np.arange(3), 0)
