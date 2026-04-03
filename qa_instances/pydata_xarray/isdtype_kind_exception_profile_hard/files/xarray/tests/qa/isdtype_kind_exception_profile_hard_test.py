from __future__ import annotations

import numpy as np
import pytest

from xarray.core.dtypes import isdtype


class TestIsDtypeKindExceptionProfileHardQA:
    def test_isdtype_kind_exception_profile_hard_case(self) -> None:
        expected_exception_kind = TypeError.__name__

        with pytest.raises(TypeError) as exc_info:
            isdtype(np.dtype("int64"), 123)  # invalid `kind` type

        observed_exception_kind = type(exc_info.value).__name__
        observed_exception_message = str(exc_info.value)

        assert observed_exception_kind == expected_exception_kind
        assert isinstance(observed_exception_message, str)
        assert len(observed_exception_message) > 10
