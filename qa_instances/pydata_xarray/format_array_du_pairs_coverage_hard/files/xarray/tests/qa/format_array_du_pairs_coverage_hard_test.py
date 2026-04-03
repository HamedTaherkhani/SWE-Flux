from __future__ import annotations

import numpy as np

from xarray.core.formatting import format_array_flat


class TestFormatArrayDUPairsCoverageHardQA:
    def test_format_array_du_pairs_coverage_hard_case(self) -> None:
        arr = np.array([10, 20, 30, 40, 50, 60, 70], dtype=np.int64)

        compact = format_array_flat(arr, max_width=11)
        wide = format_array_flat(arr, max_width=80)
        tiny = format_array_flat(arr, max_width=3)

        assert isinstance(compact, str)
        assert isinstance(wide, str)
        assert isinstance(tiny, str)
        assert len(wide) >= len(compact)
        assert len(tiny) <= 3
