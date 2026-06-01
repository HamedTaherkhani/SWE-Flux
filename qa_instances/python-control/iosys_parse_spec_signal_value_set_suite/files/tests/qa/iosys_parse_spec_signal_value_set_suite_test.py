from control.iosys import _parse_spec
from control.statesp import ss


def _systems():
    return [
        ss([], [], [], [[1.0, 0.0], [0.0, 1.0]], name="plant",
           inputs=["cmd", "trim"], outputs=["pos", "vel"]),
        ss([], [], [], [[1.0], [2.0], [3.0]], name="sensor",
           inputs=["raw"], outputs=["north", "east", "down"]),
        ss([], [], [], [[1.0, 0.5, -0.5]], name="mixer",
           inputs=["left", "right", "bias"], outputs=["mix"]),
    ]


def _run(spec, signame="output", dictname=None):
    system_index, signal_indices, gain = _parse_spec(
        _systems(), spec, signame, dictname=dictname)
    assert isinstance(system_index, int)
    assert isinstance(signal_indices, list)
    assert gain in {-1, 1, 2}
    return system_index, signal_indices, gain


class TestParseSpecSignalValueSetQA:
    def test_case_01(self):
        assert _run("plant.pos")[1] == [0]

    def test_case_02(self):
        assert _run("plant.-vel")[2] == -1

    def test_case_03(self):
        assert _run(("sensor", "north"))[1] == [0]

    def test_case_04(self):
        assert _run(("sensor", "east", 2))[2] == 2

    def test_case_05(self):
        assert _run(("sensor", "-down"))[2] == -1

    def test_case_06(self):
        assert _run("mixer.mix")[1] == [0]

    def test_case_07(self):
        assert _run(("plant", "cmd"), "input")[1] == [0]

    def test_case_08(self):
        assert _run(("plant", "-trim"), "input")[2] == -1

    def test_case_09(self):
        assert _run(("mixer", "left"), "input")[1] == [0]

    def test_case_10(self):
        assert _run(("mixer", "bias"), "input")[1] == [2]
