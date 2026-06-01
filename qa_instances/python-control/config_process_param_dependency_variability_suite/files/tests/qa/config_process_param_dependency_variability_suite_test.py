import warnings

from control.config import _process_param


ALIASES = {
    "timepts": (["T", "time"], ["time_points", "tout"]),
}


def _call(kwargs, defval="default-source", sigval=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _process_param("timepts", defval, kwargs.copy(), ALIASES, sigval=sigval)


class TestProcessParamDependencyVariabilityQA:
    def test_case_01(self):
        assert _call({}) == "default-source"

    def test_case_02(self):
        assert _call({"timepts": "canonical-02"}, defval=None) == "canonical-02"

    def test_case_03(self):
        assert _call({"T": "alias-T-03"}) == "alias-T-03"

    def test_case_04(self):
        assert _call({"time": "alias-time-04"}) == "alias-time-04"

    def test_case_05(self):
        assert _call({"time_points": "legacy-time-points-05"}) == "legacy-time-points-05"

    def test_case_06(self):
        assert _call({"tout": "legacy-tout-06"}) == "legacy-tout-06"

    def test_case_07(self):
        assert _call({"timepts": "canonical-07"}, defval=None, sigval=None) == "canonical-07"

    def test_case_08(self):
        assert _call({"T": "shared-08", "timepts": "shared-08"}, defval=None) == "shared-08"

    def test_case_09(self):
        assert _call({"time": "shared-09", "time_points": "shared-09"}) == "shared-09"

    def test_case_10(self):
        assert _call({"tout": "legacy-tout-10", "T": "legacy-tout-10"}) == "legacy-tout-10"
