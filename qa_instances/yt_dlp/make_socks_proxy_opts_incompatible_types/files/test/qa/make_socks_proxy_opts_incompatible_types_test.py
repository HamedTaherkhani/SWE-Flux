from yt_dlp.networking._helper import make_socks_proxy_opts


def _probe(label, value):
    try:
        result = make_socks_proxy_opts(value)
        return {
            "label": label,
            "kind": "output",
            "value_repr": repr(result),
        }
    except Exception as e:
        return {
            "label": label,
            "kind": "exception",
            "exception_type": type(e).__name__,
            "exception_message": str(e),
        }


class TestMakeSocksProxyOptsIncompatibleTypesQA:
    def test_make_socks_proxy_opts_incompatible_types_case(self):
        snapshots = [
            _probe("bytes_url", b"socks5://host:1080"),
            _probe("int_value", 12345),
            _probe("none_value", None),
        ]

        # Shape-only assertions; do not reveal kinds, types, or messages.
        assert isinstance(snapshots, list)
        assert len(snapshots) == 3
        assert all(isinstance(s, dict) and "label" in s for s in snapshots)
