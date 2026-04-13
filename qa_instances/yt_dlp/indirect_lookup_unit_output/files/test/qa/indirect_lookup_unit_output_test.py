from yt_dlp.utils._utils import parse_bytes


class TestIndirectLookupUnitOutputQA:
    def test_indirect_lookup_unit_output_case(self) -> None:
        result = parse_bytes("12.5M")
        assert isinstance(result, int)
        assert result > 0
