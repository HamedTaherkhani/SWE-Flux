from __future__ import annotations

import datetime as dtm

import pytest

from telegram._utils.datetime import UTC, to_float_timestamp, to_timestamp


class TestUtilsDatetimeTzinfoInvariantSuiteQA:
    def test_case_01_naive_time_default_tz(self):
        result = to_float_timestamp(dtm.time(12, 30), reference_timestamp=1_700_000_000.0)
        assert isinstance(result, float)

    def test_case_02_naive_time_explicit_utc(self):
        result = to_float_timestamp(
            dtm.time(6, 15),
            reference_timestamp=1_700_000_100.0,
            tzinfo=UTC,
        )
        assert isinstance(result, float)

    def test_case_03_aware_time_utc(self):
        result = to_float_timestamp(
            dtm.time(6, 15, tzinfo=UTC),
            reference_timestamp=1_700_000_200.0,
        )
        assert isinstance(result, float)

    def test_case_04_aware_time_positive_offset(self):
        tz = dtm.timezone(dtm.timedelta(hours=3))
        result = to_float_timestamp(
            dtm.time(9, 45, tzinfo=tz),
            reference_timestamp=1_700_000_300.0,
        )
        assert isinstance(result, float)

    def test_case_05_naive_time_rolls_to_next_day(self):
        # reference is 23:59 UTC, target time is 00:01
        result = to_float_timestamp(
            dtm.time(0, 1),
            reference_timestamp=1_704_067_140.0,
            tzinfo=UTC,
        )
        assert result > 1_704_067_140.0

    def test_case_06_naive_time_same_day(self):
        result = to_float_timestamp(
            dtm.time(22, 0),
            reference_timestamp=1_704_058_000.0,
            tzinfo=UTC,
        )
        assert result >= 1_704_058_000.0

    def test_case_07_timedelta_positive(self):
        result = to_float_timestamp(dtm.timedelta(minutes=7), reference_timestamp=900.0)
        assert result == 1320.0

    def test_case_08_timedelta_negative(self):
        result = to_float_timestamp(dtm.timedelta(seconds=-45), reference_timestamp=900.0)
        assert result == 855.0

    def test_case_09_float_relative_seconds(self):
        result = to_float_timestamp(12.5, reference_timestamp=1000.0)
        assert result == 1012.5

    def test_case_10_int_relative_seconds(self):
        result = to_float_timestamp(8, reference_timestamp=1000.0)
        assert result == 1008.0

    def test_case_11_naive_datetime(self):
        result = to_float_timestamp(dtm.datetime(2024, 1, 1, 12, 0, 0), tzinfo=UTC)
        assert isinstance(result, float)

    def test_case_12_aware_datetime(self):
        tz = dtm.timezone(dtm.timedelta(hours=-4))
        result = to_float_timestamp(dtm.datetime(2024, 6, 1, 8, 30, 0, tzinfo=tz))
        assert isinstance(result, float)

    def test_case_13_datetime_with_reference_raises(self):
        with pytest.raises(ValueError):
            to_float_timestamp(
                dtm.datetime(2024, 1, 1, 12, 0, 0),
                reference_timestamp=1_000_000.0,
            )

    def test_case_14_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            to_float_timestamp("not-a-time")  # type: ignore[arg-type]

    def test_case_15_to_timestamp_with_time(self):
        result = to_timestamp(
            dtm.time(13, 0),
            reference_timestamp=1_700_010_000.0,
            tzinfo=UTC,
        )
        assert isinstance(result, int)

    def test_case_16_to_timestamp_none(self):
        assert to_timestamp(None) is None

    def test_case_17_naive_time_custom_tz(self):
        tz = dtm.timezone(dtm.timedelta(hours=5, minutes=30))
        result = to_float_timestamp(
            dtm.time(5, 10),
            reference_timestamp=1_700_020_000.0,
            tzinfo=tz,
        )
        assert isinstance(result, float)

    def test_case_18_aware_time_with_other_tz_arg(self):
        time_tz = dtm.timezone(dtm.timedelta(hours=1))
        arg_tz = dtm.timezone(dtm.timedelta(hours=-2))
        result = to_float_timestamp(
            dtm.time(3, 5, tzinfo=time_tz),
            reference_timestamp=1_700_030_000.0,
            tzinfo=arg_tz,
        )
        assert isinstance(result, float)
