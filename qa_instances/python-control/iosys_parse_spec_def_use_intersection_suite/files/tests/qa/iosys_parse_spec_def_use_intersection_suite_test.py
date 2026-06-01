from control.iosys import _parse_spec
from control.statesp import ss


def _systems():
    plant = ss(
        [[0.0, 1.0], [-2.0, -3.0]],
        [[1.0, 0.0], [0.0, 1.0]],
        [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
        [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        name="plant",
        inputs=["cmd", "dist"],
        outputs=["pos", "vel", "sum"],
        states=["x0", "x1"],
    )
    observer = ss(
        [[-4.0]],
        [[1.0, 0.5]],
        [[2.0], [-1.0]],
        [[0.0, 0.0], [0.0, 0.0]],
        name="observer",
        inputs=["meas", "bias"],
        outputs=["estimate", "residual"],
        states=["z"],
    )
    gain = ss(
        [],
        [],
        [],
        [[1.0, -1.0], [0.25, 0.75]],
        name="gain",
        inputs=["left", "right"],
        outputs=["mix", "trim"],
    )
    return [plant, observer, gain]


def _assert_parse_result(result, system_index, signal_index, gain):
    assert result == (system_index, [signal_index], gain)


class TestParseSpecDefUseIntersectionQA:
    def test_case_01(self):
        out = _parse_spec(_systems(), ("plant", "pos"), "output")
        _assert_parse_result(out, 0, 0, 1)

    def test_case_02(self):
        out = _parse_spec(_systems(), ("plant", "vel", 2.0), "output")
        _assert_parse_result(out, 0, 1, 2.0)

    def test_case_03(self):
        out = _parse_spec(_systems(), ("plant", "sum", -0.5), "output")
        _assert_parse_result(out, 0, 2, -0.5)

    def test_case_04(self):
        out = _parse_spec(_systems(), ("observer", "estimate"), "output")
        _assert_parse_result(out, 1, 0, 1)

    def test_case_05(self):
        out = _parse_spec(_systems(), ("observer", "residual", 3), "output")
        _assert_parse_result(out, 1, 1, 3)

    def test_case_06(self):
        out = _parse_spec(_systems(), ("gain", "mix"), "output")
        _assert_parse_result(out, 2, 0, 1)

    def test_case_07(self):
        out = _parse_spec(_systems(), ("gain", "trim", -2), "output")
        _assert_parse_result(out, 2, 1, -2)

    def test_case_08(self):
        out = _parse_spec(_systems(), ("plant", "cmd"), "input")
        _assert_parse_result(out, 0, 0, 1)

    def test_case_09(self):
        out = _parse_spec(_systems(), ("observer", "bias", 0.25), "input")
        _assert_parse_result(out, 1, 1, 0.25)

    def test_case_10(self):
        out = _parse_spec(_systems(), ("gain", "right"), "input")
        _assert_parse_result(out, 2, 1, 1)
