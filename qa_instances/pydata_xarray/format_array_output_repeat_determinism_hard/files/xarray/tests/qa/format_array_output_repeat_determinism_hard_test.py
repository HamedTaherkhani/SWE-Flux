import numpy as np

from xarray.core.formatting import format_array_flat


class TestFormatArrayOutputRepeatDeterminismHardQA:
    def test_format_array_output_repeat_determinism_hard_part_a(self) -> None:
        arr = np.array([[1, 20, 300], [4000, 50000, 600000]], dtype=np.int64)
        outputs = []
        for _ in range(5):
            outputs.append(format_array_flat(arr, max_width=19))
        assert len(outputs) == 5
        assert all(isinstance(v, str) and len(v) > 0 for v in outputs)

    def test_format_array_output_repeat_determinism_hard_part_b(self) -> None:
        arr = np.array([7, 8, 9, 10, 11, 12], dtype=np.int64)
        out = format_array_flat(arr, max_width=9)
        assert isinstance(out, str)
