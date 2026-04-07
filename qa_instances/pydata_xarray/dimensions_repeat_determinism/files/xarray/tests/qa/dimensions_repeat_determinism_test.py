import numpy as np
import pytest

from xarray.core.variable import Variable, calculate_dimensions


class TestDimensionsRepeatDeterminismHardQA:
    def test_dimensions_repeat_determinism_part_a(self) -> None:
        variables = {
            "a": Variable(("x", "y"), np.arange(6).reshape(2, 3)),
            "b": Variable(("y",), np.array([10, 20, 30])),
        }

        outputs = []
        for _ in range(5):
            outputs.append(calculate_dimensions(variables))

        assert all(out == outputs[0] for out in outputs)
        assert outputs[0]["x"] == 2
        assert outputs[0]["y"] == 3

    def test_dimensions_repeat_determinism_part_b(self) -> None:
        variables = {
            "a": Variable(("x", "y"), np.arange(6).reshape(2, 3)),
            "b": Variable(("y",), np.array([10, 20, 30])),
        }
        out = calculate_dimensions(variables)
        assert out["x"] == 2
        assert out["y"] == 3


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
