from yt_dlp.dispatching import run_dispatch


class TestDispatchProcessDynamicTargetQA:
    def test_dispatch_process_dynamic_target_case(self) -> None:
        payload = "  PATH=/a/./b/../c  token=AbCDef_9012  "
        out = run_dispatch(payload)
        assert isinstance(out, int)
        assert 0 <= out < 65536
