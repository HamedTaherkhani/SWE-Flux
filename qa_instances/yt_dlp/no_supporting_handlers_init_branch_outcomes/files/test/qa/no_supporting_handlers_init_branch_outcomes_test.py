from yt_dlp.networking.exceptions import NoSupportingHandlers, UnsupportedRequest


class _StubHandler:
    def __init__(self, name):
        self.RH_NAME = name


def _err(msg, handler_name):
    err = UnsupportedRequest(msg=msg)
    err.handler = _StubHandler(handler_name)
    return err


class TestNoSupportingHandlersInitBranchOutcomesQA:
    def test_with_unsupported_only(self):
        e = NoSupportingHandlers(
            unsupported_errors=[_err("Proxy not supported", "UrllibRH")],
            unexpected_errors=[],
        )
        assert isinstance(str(e), str)

    def test_with_unexpected_only(self):
        e = NoSupportingHandlers(
            unsupported_errors=[],
            unexpected_errors=[ValueError("boom")],
        )
        assert isinstance(str(e), str)

    def test_with_two_unsupported_same_msg(self):
        e = NoSupportingHandlers(
            unsupported_errors=[
                _err("Proxy not supported", "UrllibRH"),
                _err("Proxy not supported", "RequestsRH"),
            ],
            unexpected_errors=[],
        )
        assert isinstance(str(e), str)
