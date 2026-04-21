from yt_dlp.networking.common import Request, RequestDirector, RequestHandler
from yt_dlp.networking.exceptions import NoSupportingHandlers


class _SilentLogger:
    def stdout(self, msg):
        return None

    def error(self, msg, is_error=False):
        return None


class _RejectBySchemeRH(RequestHandler):
    _SUPPORTED_URL_SCHEMES = ("http",)
    _SUPPORTED_PROXY_SCHEMES = ()

    def _send(self, request):
        raise RuntimeError("unreachable")


class _ValueErrorSendRH(RequestHandler):
    _SUPPORTED_URL_SCHEMES = ("https",)
    _SUPPORTED_PROXY_SCHEMES = ()

    def _send(self, request):
        return int("not-an-int")


class TestRequestDirectorCaughtExceptionKindsQA:
    def test_request_director_caught_exception_kinds_case(self) -> None:
        logger = _SilentLogger()
        director = RequestDirector(logger=logger, verbose=False)
        director.add_handler(_RejectBySchemeRH(logger=logger))
        director.add_handler(_ValueErrorSendRH(logger=logger))
        req = Request("https://example.com/resource")

        try:
            director.send(req)
            raise AssertionError("Expected NoSupportingHandlers")
        except NoSupportingHandlers:
            pass
