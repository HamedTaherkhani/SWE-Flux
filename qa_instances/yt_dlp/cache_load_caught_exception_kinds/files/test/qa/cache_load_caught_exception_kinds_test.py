import os
import tempfile

from yt_dlp.cache import Cache


class _StubYDL:
    def __init__(self, cachedir):
        self.params = {"cachedir": cachedir}

    def write_debug(self, msg):
        pass

    def report_warning(self, msg):
        pass


SECTION = "qa"


class TestCacheLoadCaughtExceptionKindsQA:
    def test_cache_load_caught_exception_kinds_case(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl = _StubYDL(tmpdir)
            cache = Cache(ydl)

            # Scenario A: cache file present but contents are not valid JSON.
            path_a = cache._get_cache_fn(SECTION, "alpha", "json")
            os.makedirs(os.path.dirname(path_a), exist_ok=True)
            with open(path_a, "w", encoding="utf-8") as f:
                f.write("this is not json")
            cache.load(SECTION, "alpha")

            # Scenario B: cache file present, valid JSON, but missing the
            # expected payload key.
            path_b = cache._get_cache_fn(SECTION, "beta", "json")
            with open(path_b, "w", encoding="utf-8") as f:
                f.write('{"yt-dlp_version": "2024.01.01"}')
            cache.load(SECTION, "beta")

            # Scenario C: cache file does not exist on disk.
            cache.load(SECTION, "gamma")
