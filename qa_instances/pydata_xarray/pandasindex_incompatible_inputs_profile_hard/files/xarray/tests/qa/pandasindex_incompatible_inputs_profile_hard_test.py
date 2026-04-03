from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from xarray.core.indexes import PandasIndex


class TestPandasIndexIncompatibleInputsProfileHardQA:
    def test_pandasindex_incompatible_inputs_profile_hard_case(self) -> None:
        pidx = PandasIndex(pd.Index([0, 2, 4], name="x"), dim="x", coord_dtype=np.int64)

        with pytest.raises(TypeError) as exc_type_mismatch:
            pidx.sel({"x": 2}, method=7)
        with pytest.raises(ValueError) as exc_label_mismatch:
            pidx.sel({"x": {"left": 2}})

        case_one_exception_kind = type(exc_type_mismatch.value).__name__
        case_one_exception_message = str(exc_type_mismatch.value)
        case_two_exception_kind = type(exc_label_mismatch.value).__name__
        case_two_exception_message = str(exc_label_mismatch.value)

        assert case_one_exception_kind == TypeError.__name__
        assert case_two_exception_kind == ValueError.__name__
        assert len(case_one_exception_message) > 5
        assert len(case_two_exception_message) > 10
