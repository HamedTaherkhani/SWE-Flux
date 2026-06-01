from control.iosys import _parse_spec
from control.statesp import ss


def _systems():
    plant = ss(
        [[0.0]], [[1.0, 0.0]], [[1.0], [2.0]], [[0.0, 0.0], [0.0, 0.0]],
        name="plant", inputs=["cmd", "dist"], outputs=["pos", "vel"])
    gain = ss(
        [], [], [], [[1.0, -1.0], [2.0, 3.0]],
        name="gain", inputs=["left", "right"], outputs=["mix", "trim"])
    return [plant, gain]


class TestParseSpecGainDependencyVariabilityQA:
    def test_case_01(self):
        assert _parse_spec(_systems(), ("plant", "pos"), "output") == (0, [0], 1)

    def test_case_02(self):
        assert _parse_spec(_systems(), ("plant", "vel", 2.5), "output") == (0, [1], 2.5)

    def test_case_03(self):
        assert _parse_spec(_systems(), "-plant.pos", "output") == (0, [0], -1)

    def test_case_04(self):
        assert _parse_spec(_systems(), ("plant", "-vel"), "output") == (0, [1], -1)

    def test_case_05(self):
        assert _parse_spec(_systems(), ("gain", "mix", -3), "output") == (1, [0], -3)

    def test_case_06(self):
        assert _parse_spec(_systems(), "-gain.trim", "output") == (1, [1], -1)

    def test_case_07(self):
        assert _parse_spec(_systems(), ("gain", "-right"), "input") == (1, [1], -1)

    def test_case_08(self):
        assert _parse_spec(_systems(), ("plant", "cmd", 0.25), "input") == (0, [0], 0.25)

    def test_case_09(self):
        assert _parse_spec(_systems(), "gain.left", "input") == (1, [0], 1)

    def test_case_10(self):
        assert _parse_spec(_systems(), ("plant", "dist"), "input") == (0, [1], 1)
