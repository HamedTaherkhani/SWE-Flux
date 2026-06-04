from __future__ import annotations

import pybamm


class TestBatteryModelOptionsInitDefUseIntersectionQA:
    def _build(self, options):
        parsed_options = pybamm.BatteryModelOptions(options)
        assert parsed_options["working electrode"] in ["both", "positive"]
        return parsed_options

    def test_case_01(self):
        model = self._build({
            "thermal": "lumped",
            "cell geometry": "pouch",
            "calculate discharge energy": "true",
            "SEI": "reaction limited",
            "SEI film resistance": "distributed",
            "particle mechanics": ("swelling only", "none"),
            "loss of active material": ("stress-driven", "none"),
        })
        assert model["total interfacial current density as a state"] == "true"

    def test_case_02(self):
        model = self._build({
            "particle": ("uniform profile", "quadratic profile"),
            "open-circuit potential": ("current sigmoid", "single"),
            "intercalation kinetics": ("linear", "Marcus"),
            "exchange-current density": ("single", "current sigmoid"),
        })
        assert model["particle"][0] == "uniform profile"

    def test_case_03(self):
        model = self._build({
            "lithium plating": "reversible",
            "lithium plating porosity change": "true",
            "SEI": "solvent-diffusion limited",
            "SEI porosity change": "true",
            "x-average side reactions": "true",
        })
        assert model["lithium plating"][0] == "reversible"

    def test_case_04(self):
        model = self._build({
            "working electrode": "positive",
            "SEI": "electron-migration limited",
            "lithium plating": "irreversible",
            "particle mechanics": "swelling only",
            "surface form": "differential",
        })
        assert model["working electrode"] == "positive"

    def test_case_05(self):
        model = self._build({
            "particle phases": ("2", "1"),
            "surface form": "algebraic",
            "SEI": "reaction limited",
            "SEI film resistance": "average",
            "total interfacial current density as a state": "true",
        })
        assert model["particle phases"][0] == "2"

    def test_case_06(self):
        model = self._build({
            "thermal": "lumped",
            "cell geometry": "pouch",
            "surface temperature": "lumped",
            "use lumped thermal capacity": "true",
            "calculate heat source for isothermal models": "true",
        })
        assert model["thermal"] == "lumped"

    def test_case_07(self):
        model = self._build({
            "operating mode": "voltage",
            "voltage as a state": "true",
            "interface utilisation": "current-driven",
            "exchange-current density": "current sigmoid",
        })
        assert model["operating mode"] == "voltage"

    def test_case_08(self):
        model = self._build({
            "particle size": "distribution",
            "surface form": "algebraic",
            "particle": "Fickian diffusion",
            "SEI": "none",
            "lithium plating porosity change": "false",
            "SEI porosity change": "false",
        })
        assert model["particle size"] == "distribution"

    def test_case_09(self):
        model = self._build({
            "open-circuit potential": "MSMR",
            "particle": "MSMR",
            "intercalation kinetics": "MSMR",
            "number of MSMR reactions": ("3", "2"),
        })
        assert model["particle"] == "MSMR"

    def test_case_10(self):
        model = self._build({
            "contact resistance": "true",
            "operating mode": "current",
            "calculate heat source for isothermal models": "true",
            "heat of mixing": "true",
        })
        assert model["contact resistance"] == "true"
