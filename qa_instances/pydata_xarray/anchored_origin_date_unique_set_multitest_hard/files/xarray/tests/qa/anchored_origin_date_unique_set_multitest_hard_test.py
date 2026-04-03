import datetime

import cftime

from xarray.coding.cftime_offsets import to_offset
from xarray.core.resample_cftime import _adjust_dates_anchored


class TestAnchoredOriginDateUniqueSetMultitestHardQA:
    def test_anchored_origin_date_unique_set_multitest_hard_part_a(self) -> None:
        first = cftime.DatetimeNoLeap(2001, 1, 1, 6)
        last = cftime.DatetimeNoLeap(2001, 1, 4, 6)
        freq = to_offset("2D")

        r1 = _adjust_dates_anchored(
            first, last, freq, closed="left", origin="start_day", offset=None
        )
        r2 = _adjust_dates_anchored(
            first, last, freq, closed="left", origin="start", offset=None
        )
        r3 = _adjust_dates_anchored(
            first,
            last,
            freq,
            closed="left",
            origin="epoch",
            offset=datetime.timedelta(hours=6),
        )

        assert len(r1) == len(r2) == len(r3) == 2
        assert r1[0] <= r1[1]
        assert r2[0] <= r2[1]
        assert r3[0] <= r3[1]

    def test_anchored_origin_date_unique_set_multitest_hard_part_b(self) -> None:
        first = cftime.DatetimeNoLeap(2001, 1, 1, 6)
        last = cftime.DatetimeNoLeap(2001, 1, 4, 6)
        freq = to_offset("2D")

        r4 = _adjust_dates_anchored(
            first, last, freq, closed="left", origin="end_day", offset=None
        )
        r5 = _adjust_dates_anchored(
            first,
            last,
            freq,
            closed="left",
            origin=cftime.DatetimeNoLeap(1999, 12, 31, 0),
            offset=datetime.timedelta(hours=3),
        )

        assert len(r4) == len(r5) == 2
        assert r4[0] <= r4[1]
        assert r5[0] <= r5[1]
