import numpy as np

from xarray.coding.times import _eagerly_encode_cf_datetime


class TestCFTimeDeltaConditionSnapshotHardQA:
    def test_cf_time_delta_condition_snapshot_case(self) -> None:
        dates = np.array(
            [
                "2000-01-01T00:00:00.000000000",
                "2000-01-01T01:00:00.000000000",
                "2000-01-01T02:00:00.000000000",
            ],
            dtype="datetime64[ns]",
        )

        num, units, calendar = _eagerly_encode_cf_datetime(
            dates=dates,
            units="days since 2000-01-01 00:00:00",
            calendar="proleptic_gregorian",
            dtype=None,
            allow_units_modification=False,
        )

        assert num.shape == dates.shape
        assert isinstance(units, str)
        assert calendar == "proleptic_gregorian"
