from yt_dlp.utils.networking import normalize_url


class TestNetworkingFunctionCallOrderQA:
    def test_networking_function_call_order_case(self) -> None:
        out = normalize_url("https://example.com/a/./b/../c;d?e=f#frag")
        assert isinstance(out, str)
        assert out.startswith("https://example.com/")
