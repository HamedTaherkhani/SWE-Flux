import numpy as np

from xarray.core.variable import Variable, calculate_dimensions


class TestDimensionsRepeatDeterminismHardQA:
    def test_dimensions_repeat_determinism_hard_part_a(self) -> None:
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

    def test_dimensions_repeat_determinism_hard_part_b(self) -> None:
        variables = {
            "a": Variable(("x", "y"), np.arange(6).reshape(2, 3)),
            "b": Variable(("y",), np.array([10, 20, 30])),
        }
        out = calculate_dimensions(variables)
        assert out["x"] == 2
        assert out["y"] == 3
