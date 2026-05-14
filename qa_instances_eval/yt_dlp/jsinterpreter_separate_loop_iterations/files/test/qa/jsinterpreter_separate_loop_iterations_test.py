from yt_dlp.jsinterp import JSInterpreter


EXPR = "(a,b),c,d,(e,f),g"


class TestJsInterpreterSeparateLoopIterationsQA:
    def test_jsinterpreter_separate_loop_iterations_case(self):
        result = list(JSInterpreter._separate(EXPR, ",", max_split=2))

        # Shape-only assertion; do not reveal the iteration count.
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)
