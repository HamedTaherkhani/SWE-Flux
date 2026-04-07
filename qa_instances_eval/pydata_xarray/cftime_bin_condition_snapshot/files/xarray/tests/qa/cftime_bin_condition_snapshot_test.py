import cftime

from xarray.coding.cftimeindex import CFTimeIndex
from xarray.core.resample_cftime import CFTimeGrouper


class TestCFTimeBinConditionSnapshotHardQA:
    def test_cftime_bin_condition_snapshot_case(self) -> None:
        index = CFTimeIndex(
            [
                cftime.DatetimeNoLeap(2001, 1, 1, 6),
                cftime.DatetimeNoLeap(2001, 1, 1, 18),
                cftime.DatetimeNoLeap(2001, 1, 2, 6),
                cftime.DatetimeNoLeap(2001, 1, 2, 18),
                cftime.DatetimeNoLeap(2001, 1, 3, 6),
                cftime.DatetimeNoLeap(2001, 1, 3, 18),
                cftime.DatetimeNoLeap(2001, 1, 4, 6),
            ]
        )

        grouper = CFTimeGrouper(
            freq="2D",
            closed="left",
            label="left",
            origin="start_day",
            offset="12h",
        )
        first_items, codes = grouper.first_items(index)

        assert len(codes) == len(index)
        assert first_items.size > 0
