import pybamm


class TestLithiumIonSPMInitCallCoverageQA:
    def _construct(self, case, options):
        model = pybamm.lithium_ion.SPM(options, name=f"qa complex spm {case}")
        assert model.submodels
        assert model.variables
        assert model.rhs or model.algebraic
        return model

    def test_case_01(self):
        assert self._construct(1, {})

    def test_case_02(self):
        assert self._construct(
            2, {"surface form": "algebraic", "particle size": "distribution"}
        )

    def test_case_03(self):
        assert self._construct(3, {"thermal": "x-full"})

    def test_case_04(self):
        assert self._construct(
            4,
            {
                "particle": "quadratic profile",
                "particle mechanics": "swelling and cracking",
                "stress-induced diffusion": "true",
            },
        )

    def test_case_05(self):
        assert self._construct(
            5, {"particle": "uniform profile", "intercalation kinetics": "linear"}
        )

    def test_case_06(self):
        assert self._construct(
            6,
            {
                "SEI": "ec reaction limited",
                "SEI porosity change": "true",
                "lithium plating": "irreversible",
                "lithium plating porosity change": "true",
            },
        )

    def test_case_07(self):
        assert self._construct(7, {"working electrode": "positive"})

    def test_case_08(self):
        assert self._construct(
            8,
            {
                "particle phases": ("2", "1"),
                "open-circuit potential": (("single", "current sigmoid"), "single"),
            },
        )

    def test_case_09(self):
        assert self._construct(
            9,
            {
                "surface form": "differential",
                "intercalation kinetics": "Marcus",
                "exchange-current density": "single",
            },
        )

    def test_case_10(self):
        assert self._construct(
            10,
            {
                "contact resistance": "true",
                "operating mode": "voltage",
                "calculate discharge energy": "true",
            },
        )
