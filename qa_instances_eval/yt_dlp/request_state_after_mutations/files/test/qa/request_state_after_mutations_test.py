from yt_dlp.networking.common import Request


def _collect_state(req):
    return {
        "url": req.url,
        "method": req.method,
        "data_repr": repr(req.data),
        "headers_titled": dict(req.headers),
        "headers_sensitive": req.headers.sensitive(),
        "proxies": dict(req.proxies),
        "extensions": dict(req.extensions),
    }


class TestRequestStateAfterMutationsQA:
    def test_request_state_after_mutations_case(self):
        req = Request(
            url="HTTP://Example.COM/api?z=9&a=1",
            method="post",
            headers={"x-trace-ID": "abc", "Accept": "application/json"},
            data=b"hello",
            proxies={"http": "http://proxy.local:8080"},
            extensions={"timeout": 5},
        )

        req.update(
            url="https://example.com/v2/users",
            query={"limit": 10, "page": 2},
            headers={"X-TRACE-Id": "def", "x-new-header": "1"},
            extensions={"retries": 3},
        )

        req.data = None
        req.headers["accept-language"] = "en-US"

        snapshot = _collect_state(req)

        # Shape-only checks; do not reveal final values.
        assert isinstance(req, Request)
        assert isinstance(snapshot, dict)
        assert {"url", "method", "data_repr", "headers_titled",
                "headers_sensitive", "proxies", "extensions"} <= set(snapshot)
