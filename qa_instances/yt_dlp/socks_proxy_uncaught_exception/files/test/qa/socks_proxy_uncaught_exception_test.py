import pytest

from yt_dlp.networking._helper import make_socks_proxy_opts


class TestSocksProxyUncaughtExceptionQA:
    def test_socks_proxy_uncaught_exception_case(self) -> None:
        with pytest.raises(Exception):
            make_socks_proxy_opts("socks://127.0.0.1")
