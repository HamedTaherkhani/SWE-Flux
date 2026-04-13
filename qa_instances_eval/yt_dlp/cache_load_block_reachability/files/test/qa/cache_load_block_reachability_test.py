import os
import tempfile

from yt_dlp.cache import Cache


class _DummyYDL:
    def __init__(self, cachedir: str):
        self.params = {"cachedir": cachedir}

    def write_debug(self, msg: str) -> None:
        pass

    def report_warning(self, msg: str) -> None:
        pass

    def to_screen(self, msg: str, **kwargs) -> None:
        pass


class TestCacheLoadBlockReachabilityQA:
    def test_cache_load_block_reachability_case(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ydl = _DummyYDL(cachedir=td)
            cache = Cache(ydl)

            cache_fn = cache._get_cache_fn("sec", "k", "json")
            os.makedirs(os.path.dirname(cache_fn), exist_ok=True)
            with open(cache_fn, "wb") as f:
                f.write(b"{")

            out = cache.load("sec", "k", default={"d": 1})
            assert out == {"d": 1}
