from yt_dlp.utils._utils import unified_timestamp


class TestUnifiedTimestampHelperIndirectOutputQA:
    def test_unified_timestamp_helper_indirect_output_case(self):
        date_str = "Wednesday|2024-08-14T06:30:45.987-04:30"
        ts = unified_timestamp(date_str)

        assert ts is not None
        assert isinstance(ts, int)
