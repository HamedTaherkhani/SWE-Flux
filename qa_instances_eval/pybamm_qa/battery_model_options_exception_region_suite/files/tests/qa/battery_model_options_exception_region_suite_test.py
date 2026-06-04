from pybamm.models.full_battery_models.base_battery_model import BatteryModelOptions


class TestBatteryModelOptionsExceptionRegionQA:
    def _construct(self, options):
        configured = BatteryModelOptions(options)
        assert configured["particle mechanics"]
        assert configured["cell geometry"]

    def test_case_01(self):
        self._construct(
            {"particle size": "distribution", "surface form": "algebraic"}
        )

    def test_case_02(self):
        self._construct(
            {
                "particle size": "distribution",
                "surface form": "algebraic",
                "SEI porosity change": "true",
            }
        )

    def test_case_03(self):
        self._construct(
            {
                "SEI": "ec reaction limited",
                "total interfacial current density as a state": "false",
            }
        )

    def test_case_04(self):
        self._construct(
            {"particle phases": ("2", "1"), "surface form": "algebraic"}
        )

    def test_case_05(self):
        self._construct({"particle phases": "2", "surface form": "false"})

    def test_case_06(self):
        self._construct(
            {"contact resistance": "true", "operating mode": "explicit power"}
        )

    def test_case_07(self):
        self._construct({"thermal": "x-full", "cell geometry": "pouch"})

    def test_case_08(self):
        self._construct(
            {
                "thermal": "x-full",
                "dimensionality": 1,
                "current collector": "potential pair",
            }
        )

    def test_case_09(self):
        self._construct(
            {"SEI on cracks": "true", "loss of active material": "stress-driven"}
        )

    def test_case_10(self):
        self._construct(
            {"SEI on cracks": "true", "particle mechanics": "swelling only"}
        )
