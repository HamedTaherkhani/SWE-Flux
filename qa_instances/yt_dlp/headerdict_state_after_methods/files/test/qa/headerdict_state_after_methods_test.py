from yt_dlp.utils.networking import HTTPHeaderDict


class TestHeaderdictStateAfterMethodsQA:
    def test_headerdict_state_after_methods_case(self) -> None:
        headers = HTTPHeaderDict({"X-Test": " 1 "})
        headers.update({"user-agent": "Agent/1.0", "ACCEPT": " text/plain "})
        headers["x-bytes"] = b" 42 "
        headers.setdefault("x-test", "ignored")
        headers.setdefault("x-new", " value ")
        headers.pop("accept")

        state = headers.sensitive()
        assert isinstance(state, dict)
        assert "user-agent" in state
