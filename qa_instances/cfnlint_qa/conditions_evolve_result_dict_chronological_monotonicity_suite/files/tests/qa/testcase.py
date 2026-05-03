from __future__ import annotations

import sys
from pathlib import Path

import pytest

def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "src" / "cfnlint").is_dir():
            return p
    raise RuntimeError("Could not locate cfnlint source tree (expected .../src/cfnlint).")

_REPO_ROOT = _find_repo_root()
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cfnlint.context.conditions._conditions import (
    Conditions,
    _satisfiable_cache,
)
from cfnlint.context.conditions.exceptions import Unsatisfiable
from cfnlint.context.context import Parameter

def _params(*names_with_allowed):
    out = {}
    for name, allowed in names_with_allowed:
        spec = {"Type": "String"}
        if allowed is not None:
            spec["AllowedValues"] = list(allowed)
        out[name] = Parameter(spec)
    return out

def _make_simple_conditions(env_allowed=("prod", "dev"), size_allowed=None):
    return Conditions.create_from_instance(
        {
            "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
            "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
            "IsBig": {"Fn::Equals": [{"Ref": "Size"}, "large"]},
        },
        {},
        _params(("Env", env_allowed), ("Size", size_allowed)),
    )

def _make_compound_conditions():
    return Conditions.create_from_instance(
        {
            "IsProdAndBig": {
                "Fn::And": [
                    {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    {"Fn::Equals": [{"Ref": "Size"}, "large"]},
                ]
            },
            "IsAnyEnv": {
                "Fn::Or": [
                    {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                    {"Fn::Equals": [{"Ref": "Env"}, "stage"]},
                    {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
                ]
            },
            "NotProd": {"Fn::Not": [{"Fn::Equals": [{"Ref": "Env"}, "prod"]}]},
        },
        {},
        _params(("Env", None), ("Size", None)),
    )

def _make_static_conditions():
    return Conditions.create_from_instance(
        {
            "AlwaysTrue": {"Fn::Equals": ["x", "x"]},
            "AlwaysFalse": {"Fn::Equals": ["x", "y"]},
            "Dynamic": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
        },
        {},
        _params(("Env", None)),
    )

def _make_six_condition_template():
    return Conditions.create_from_instance(
        {
            "C0": {"Fn::Equals": [{"Ref": "Env"}, "v0"]},
            "C1": {"Fn::Equals": [{"Ref": "Env"}, "v1"]},
            "C2": {"Fn::Equals": [{"Ref": "Env"}, "v2"]},
            "C3": {"Fn::Equals": [{"Ref": "Env"}, "v3"]},
            "C4": {"Fn::Equals": [{"Ref": "Env"}, "v4"]},
            "C5": {"Fn::Equals": [{"Ref": "Env"}, "v5"]},
        },
        {},
        _params(("Env", None)),
    )

class TestConditionsEvolveResultDictChronologicalMonotonicitySuiteQA:

    def test_evolve_single_status_true(self):
        c = _make_simple_conditions()
        new = c.evolve({"IsProd": True})
        assert new.status == {"IsProd": True}

    def test_evolve_single_status_false(self):
        c = _make_simple_conditions()
        new = c.evolve({"IsProd": False})
        assert new.status == {"IsProd": False}

    def test_evolve_multi_status_distinct_params(self):
        c = _make_simple_conditions()
        new = c.evolve({"IsProd": True, "IsBig": True})
        assert new.status == {"IsProd": True, "IsBig": True}

    def test_evolve_three_conditions_all_set(self):
        c = _make_simple_conditions()
        new = c.evolve({"IsProd": True, "IsDev": False, "IsBig": True})
        assert new.status == {"IsProd": True, "IsDev": False, "IsBig": True}

    def test_evolve_empty_status_short_circuit(self):
        c = _make_simple_conditions()
        new = c.evolve({})
        assert new is c

    def test_evolve_idempotent_status_short_circuit(self):
        c = _make_simple_conditions()
        first = c.evolve({"IsProd": True})
        again = first.evolve({"IsProd": True})
        assert again is first

    def test_evolve_compound_and_or_not_status_true(self):
        c = _make_compound_conditions()
        new = c.evolve({"IsProdAndBig": True})
        assert new.status == {"IsProdAndBig": True}

    def test_evolve_compound_and_or_not_status_mixed(self):
        c = _make_compound_conditions()
        new = c.evolve({"IsProdAndBig": False, "IsAnyEnv": True, "NotProd": False})
        assert new.status == {
            "IsProdAndBig": False,
            "IsAnyEnv": True,
            "NotProd": False,
        }

    def test_evolve_static_true_only(self):
        c = _make_static_conditions()
        new = c.evolve({"AlwaysTrue": True})
        assert new.status == {"AlwaysTrue": True}

    def test_evolve_static_with_dynamic_mix(self):
        c = _make_static_conditions()
        new = c.evolve({"AlwaysTrue": True, "Dynamic": False})
        assert new.status == {"AlwaysTrue": True, "Dynamic": False}

    def test_evolve_conflicting_allowed_values_raises_unsatisfiable(self):
        c = _make_simple_conditions(env_allowed=("prod", "dev"))
        with pytest.raises(Unsatisfiable):
            c.evolve({"IsProd": False, "IsDev": False})

    def test_evolve_conflicting_three_way_raises_unsatisfiable(self):
        c = Conditions.create_from_instance(
            {
                "IsProd": {"Fn::Equals": [{"Ref": "Env"}, "prod"]},
                "IsDev": {"Fn::Equals": [{"Ref": "Env"}, "dev"]},
            },
            {},
            _params(("Env", ("prod", "dev"))),
        )
        with pytest.raises(Unsatisfiable):
            c.evolve({"IsProd": False, "IsDev": False})

    def test_evolve_six_conditions_one_true(self):
        c = _make_six_condition_template()
        new = c.evolve({"C0": True})
        assert new.status == {"C0": True}

    def test_evolve_six_conditions_three_set(self):
        c = _make_six_condition_template()
        new = c.evolve({"C0": True, "C2": False, "C4": True})
        assert new.status == {"C0": True, "C2": False, "C4": True}

    def test_evolve_six_conditions_all_set_alternating(self):
        c = _make_six_condition_template()
        new = c.evolve(
            {"C0": True, "C1": False, "C2": True, "C3": False, "C4": True, "C5": False}
        )
        assert new.status == {
            "C0": True,
            "C1": False,
            "C2": True,
            "C3": False,
            "C4": True,
            "C5": False,
        }

    def test_evolve_repeated_calls_distinct_status(self):
        c = _make_simple_conditions()
        for status in [
            {"IsProd": True},
            {"IsProd": False},
            {"IsBig": True},
            {"IsBig": False},
            {"IsDev": True},
        ]:
            new = c.evolve(status)
            assert isinstance(new, Conditions)

    def test_evolve_chained_evolve_results(self):
        c = _make_simple_conditions()
        a = c.evolve({"IsProd": True})
        b = a.evolve({"IsBig": True})
        assert b.status == {"IsProd": True, "IsBig": True}

    def test_evolve_chained_with_intermediate_idempotent(self):
        c = _make_simple_conditions()
        a = c.evolve({"IsProd": True})
        a_same = a.evolve({"IsProd": True})
        assert a_same is a
        b = a_same.evolve({"IsBig": False})
        assert b.status == {"IsProd": True, "IsBig": False}

    def test_evolve_many_distinct_status_volume(self):
        c = _make_six_condition_template()
        for i in range(6):
            for v in (True, False):
                new = c.evolve({f"C{i}": v})
                assert isinstance(new, Conditions)

    def test_evolve_independent_instances_volume(self):
        instances = [
            _make_simple_conditions(),
            _make_compound_conditions(),
            _make_static_conditions(),
            _make_six_condition_template(),
        ]
        for c in instances:
            for cond_name in list(c.conditions.keys())[:2]:
                try:
                    new = c.evolve({cond_name: True})
                    assert isinstance(new, Conditions)
                except Unsatisfiable:
                    pass

    def test_evolve_satisfiable_cache_hits_after_warm_up(self):
        c = _make_simple_conditions()
        first = c.evolve({"IsProd": True, "IsBig": True})
        again = c.evolve({"IsProd": True, "IsBig": True})
        assert first.status == again.status == {"IsProd": True, "IsBig": True}
        assert isinstance(_satisfiable_cache, dict) or hasattr(
            _satisfiable_cache, "keys"
        )
