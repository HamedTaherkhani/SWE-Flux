from yt_dlp.utils._utils import LazyList


class TestLazyListExhaustCallFrequencyQA:
    def test_lazylist_exhaust_call_frequency_case(self):
        ll = LazyList(iter(range(50)))
        a = ll[3]
        b = ll[10:15]
        c = ll[-5]
        d = ll[5:]
        e = ll[2:8:2]
        f = ll[::-1]
        g = len(ll)

        # Shape-only sanity checks; do not reveal call counts.
        assert a == 3
        assert isinstance(b, list)
        assert isinstance(c, int)
        assert isinstance(d, list)
        assert isinstance(g, int)
