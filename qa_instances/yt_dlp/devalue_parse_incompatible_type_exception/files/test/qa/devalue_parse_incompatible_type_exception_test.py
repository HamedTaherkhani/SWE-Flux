import pytest

from yt_dlp.socks import sockssocket


class TestDevalueParseIncompatibleTypeExceptionQA:
    def test_devalue_parse_incompatible_type_exception_case(self) -> None:
        with pytest.raises(Exception):
            sockssocket._len_and_data(7)
