import numpy as np

from xarray.core.dtypes import maybe_promote


class TestMaybePromotePathRepeatabilityHardQA:
    def test_maybe_promote_path_repeatability_hard_part_a(self) -> None:
        outputs = []
        for _ in range(5):
            outputs.append(maybe_promote(np.dtype("int64")))

        assert all(out[0] == outputs[0][0] for out in outputs)
        assert str(outputs[0][0]) == "float64"

    def test_maybe_promote_path_repeatability_hard_part_b(self) -> None:
        # Extra call outside the 5-run block so this is truly multi-test.
        out = maybe_promote(np.dtype("int64"))
        assert str(out[0]) == "float64"
