from control.config import defaults
from control.iosys import _process_dt_keyword


class TestProcessDtDependencyVariabilityQA:
    def test_case_01(self):
        assert _process_dt_keyword({}, {}, static=True) is None

    def test_case_02(self):
        assert _process_dt_keyword({"dt": 0.1}, {}, static=True) == 0.1

    def test_case_03(self):
        assert _process_dt_keyword({}, {"dt": 0.2}, static=True) == 0.2

    def test_case_04(self):
        assert _process_dt_keyword({"dt": True}, {"dt": 0.3}, static=False) is True

    def test_case_05(self):
        old = defaults["control.default_dt"]
        try:
            defaults["control.default_dt"] = 0.4
            assert _process_dt_keyword({}, {}, static=False) == 0.4
        finally:
            defaults["control.default_dt"] = old

    def test_case_06(self):
        assert _process_dt_keyword({"dt": None}, {"dt": 0.5}, static=False) is None

    def test_case_07(self):
        assert _process_dt_keyword({}, {"dt": True}, static=False) is True

    def test_case_08(self):
        old = defaults["control.default_dt"]
        try:
            defaults["control.default_dt"] = None
            assert _process_dt_keyword({}, {}, static=False) is None
        finally:
            defaults["control.default_dt"] = old

    def test_case_09(self):
        assert _process_dt_keyword({"dt": 0}, {}, static=True) == 0

    def test_case_10(self):
        assert _process_dt_keyword({}, {"dt": None}, static=True) is None
