from __future__ import annotations

import pybamm


class DependencySubmodel:
    rhs = {}
    algebraic = {}
    initial_conditions = {}
    boundary_conditions = {}
    variables = {}
    events = []

    def __init__(self, requires, produces, base_value):
        self.requires = requires
        self.produces = produces
        self.base_value = base_value

    def get_fundamental_variables(self):
        return {}

    def get_coupled_variables(self, variables):
        for name in self.requires:
            variables[name]
        return {
            name: pybamm.Scalar(self.base_value + index)
            for index, name in enumerate(self.produces)
        }

    def set_rhs(self, variables):
        pass

    def set_algebraic(self, variables):
        pass

    def set_boundary_conditions(self, variables):
        pass

    def set_initial_conditions(self, variables):
        pass

    def add_events_from(self, variables):
        pass


class TestBaseModelBuildCoupledVariablesDefUseIntersectionQA:
    def _build(self, seed):
        model = pybamm.BaseModel(f"qa coupled {seed}")
        model.submodels = {
            "late": DependencySubmodel((f"qa final {seed}",), [f"qa late {seed}"], seed),
            "source": DependencySubmodel((), [f"qa seed {seed}"], seed + 10),
            "middle": DependencySubmodel((f"qa seed {seed}",), [f"qa mid {seed}"], seed + 20),
            "final": DependencySubmodel((f"qa mid {seed}",), [f"qa final {seed}"], seed + 30),
        }
        model.build_model()
        assert f"qa late {seed}" in model.variables
        return model

    def test_case_01(self): assert f"qa late 1" in self._build(1).variables
    def test_case_02(self): assert f"qa late 2" in self._build(2).variables
    def test_case_03(self): assert f"qa late 3" in self._build(3).variables
    def test_case_04(self): assert f"qa late 4" in self._build(4).variables
    def test_case_05(self): assert f"qa late 5" in self._build(5).variables
    def test_case_06(self): assert f"qa late 6" in self._build(6).variables
    def test_case_07(self): assert f"qa late 7" in self._build(7).variables
    def test_case_08(self): assert f"qa late 8" in self._build(8).variables
    def test_case_09(self): assert f"qa late 9" in self._build(9).variables
    def test_case_10(self): assert f"qa late 10" in self._build(10).variables
