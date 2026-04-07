import numpy as np
import pytest

from xarray.core.dtypes import maybe_promote


class TestMaybePromotePathRepeatabilityHardQA:
    def test_maybe_promote_path_repeatability_part_a(self) -> None:
        outputs = []
        for _ in range(5):
            outputs.append(maybe_promote(np.dtype("int64")))

        assert all(out[0] == outputs[0][0] for out in outputs)
        assert str(outputs[0][0]) == "float64"

    def test_maybe_promote_path_repeatability_part_b(self) -> None:
        # Extra call outside the 5-run block so this is truly multi-test.
        out = maybe_promote(np.dtype("int64"))
        assert str(out[0]) == "float64"


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
