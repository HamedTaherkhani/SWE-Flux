from __future__ import annotations

from xarray.backends.lru_cache import LRUCache


class TestLruCacheMaxsizePostcallStateHardQA:
    def test_lru_cache_maxsize_postcall_state_case(self) -> None:
        cache = LRUCache(maxsize=4)

        cache["k1"] = 10
        cache["k2"] = 20
        cache["k3"] = 30
        _ = cache["k1"]
        cache["k4"] = 40
        cache["k5"] = 50
        _ = cache["k3"]

        cache.maxsize = 2

        post_resize_items = list(cache.items())
        post_resize_capacity = cache.maxsize
        post_resize_length = len(cache)

        assert post_resize_capacity == 2
        assert post_resize_length == 2
        assert len(post_resize_items) == 2
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in post_resize_items)
        assert "k1" not in dict(post_resize_items)
