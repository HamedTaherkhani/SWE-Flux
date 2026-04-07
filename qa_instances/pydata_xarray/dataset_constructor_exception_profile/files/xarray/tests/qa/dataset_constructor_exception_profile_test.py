from __future__ import annotations

import numpy as np
import pytest
import xarray as xr


class TestDatasetConstructorExceptionProfileHardQA:
    def test_dataset_constructor_exception_profile_case(self) -> None:
        expected_exception_kind = ValueError.__name__

        with pytest.raises(ValueError) as exc_info:
            xr.Dataset(
                data_vars={
                    "alpha": ("x", np.array([1, 2, 3], dtype=np.int64)),
                    "beta": ("x", np.array([10, 20], dtype=np.int64)),
                }
            )

        observed_exception_kind = type(exc_info.value).__name__
        observed_exception_message = str(exc_info.value)

        assert observed_exception_kind == expected_exception_kind
        assert isinstance(observed_exception_message, str)
        assert len(observed_exception_message) > 10
