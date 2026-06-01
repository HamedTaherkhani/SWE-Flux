import sys
import types
from dataclasses import dataclass

import numpy as np

from control.canonical import _bdschur_condmax_search


@dataclass
class _Profile:
    style: str
    switch_at: int | None
    condmax: float
    calls: int = 0


_CURRENT = _Profile("settle", None, 16.0)


def _matrix_with_condition(n, condition):
    mat = np.eye(n)
    mat[0, 0] = condition
    return mat


def _fake_mb03rd(n, aschur, tschur, pmax):
    del tschur
    _CURRENT.calls += 1

    if _CURRENT.calls == 1:
        condition = _CURRENT.condmax / 4.0
        defective = True
    elif _CURRENT.style == "settle":
        condition = _CURRENT.condmax / 5.0
        defective = False
    elif _CURRENT.style == "wide":
        condition = _CURRENT.condmax / 6.0
        defective = True
    else:
        phase_call = _CURRENT.calls - 1
        if phase_call < _CURRENT.switch_at:
            condition = _CURRENT.condmax / 7.0
            defective = True
        elif phase_call == _CURRENT.switch_at:
            condition = _CURRENT.condmax * 1.4
            defective = True
        else:
            condition = _CURRENT.condmax / 8.0
            defective = False

    tmodal = _matrix_with_condition(n, condition)
    amodal = np.eye(n) * (1.0 + 0.01 * _CURRENT.calls + 0.001 * pmax)
    if defective:
        blksizes = np.array([2])
        eigvals = np.array([1.0 + 0.0j, 1.0 + 0.0j])
    else:
        blksizes = np.array([1, 1])
        eigvals = np.array([1.0 + 0.0j, 2.0 + 0.0j])
    return amodal, tmodal, blksizes, eigvals


def _install(style, switch_at, condmax):
    global _CURRENT
    _CURRENT = _Profile(style, switch_at, condmax)
    sys.modules["slycot"] = types.SimpleNamespace(mb03rd=_fake_mb03rd)


def _execute(style, switch_at=None, condmax=16.0):
    _install(style, switch_at, condmax)
    aschur = np.array([[0.25, 0.0], [0.0, -0.5]])
    tschur = np.eye(2)
    amodal, tmodal, blksizes, eigvals = _bdschur_condmax_search(
        aschur, tschur, condmax)
    assert amodal.shape == (2, 2)
    assert tmodal.shape == (2, 2)
    assert blksizes.size in {1, 2}
    assert eigvals.shape == (2,)
    assert _CURRENT.calls >= 2
    return amodal


class TestCanonicalSearchTerminationQA:
    def test_case_01(self):
        out = _execute("search", switch_at=1, condmax=16.0)
        assert out[0, 0] > 1.0

    def test_case_02(self):
        out = _execute("settle", condmax=25.0)
        assert out.shape == (2, 2)

    def test_case_03(self):
        out = _execute("search", switch_at=3, condmax=36.0)
        assert np.isfinite(out).all()

    def test_case_04(self):
        out = _execute("search", switch_at=2, condmax=49.0)
        assert out[1, 1] > 1.0

    def test_case_05(self):
        out = _execute("wide", condmax=64.0)
        assert out.shape == (2, 2)

    def test_case_06(self):
        out = _execute("search", switch_at=5, condmax=81.0)
        assert np.trace(out) > 2.0

    def test_case_07(self):
        out = _execute("settle", condmax=100.0)
        assert np.isclose(out[0, 1], 0.0)

    def test_case_08(self):
        out = _execute("search", switch_at=4, condmax=121.0)
        assert out[0, 0] == out[1, 1]

    def test_case_09(self):
        out = _execute("wide", condmax=144.0)
        assert np.isfinite(out).all()

    def test_case_10(self):
        out = _execute("search", switch_at=7, condmax=169.0)
        assert out.shape == (2, 2)
