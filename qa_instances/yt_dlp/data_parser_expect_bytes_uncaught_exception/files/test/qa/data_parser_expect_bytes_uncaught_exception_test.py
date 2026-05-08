import pytest

from yt_dlp.cookies import DataParser, YDLLogger


class TestDataParserExpectBytesUncaughtExceptionQA:
    def test_data_parser_expect_bytes_uncaught_exception_case(self):
        p = DataParser(b'cookies-data', YDLLogger())
        p.expect_bytes(b'cook', 'magic1')
        p.expect_bytes(b'ies', 'magic2')
        with pytest.raises(Exception):
            p.expect_bytes(b'-XYZ', 'final')
